import json
from datetime import datetime


class StreamParser:
    """Parse Claude Code stream-json (NDJSON) output into structured events."""

    def parse_line(self, line: str) -> dict | None:
        if not line.strip():
            return None
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return {
                "event_type": "parse_error",
                "content": line,
                "is_error": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

        event_type = data.get("type", "unknown")

        event = {
            "event_type": event_type,
            "role": data.get("role"),
            "content": self._extract_content(data),
            "tool_name": None,
            "tool_input": None,
            "tool_output": None,
            "raw_json": line,
            "is_error": False,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Extract session_id from system/init or result events
        if event_type == "system" and data.get("subtype") == "init":
            event["session_id"] = data.get("session_id")
            event["event_type"] = "system_init"
        elif event_type == "system":
            event["event_type"] = "system_event"
            event["content"] = data.get("subtype", "system")
        elif event_type == "assistant":
            event["role"] = "assistant"
            # Parse content blocks: may contain text, tool_use, or thinking
            content_blocks = data.get("message", {}).get("content", []) if isinstance(data.get("message"), dict) else data.get("content", [])
            if isinstance(content_blocks, list):
                matched = False
                for block in content_blocks:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        event["event_type"] = "tool_use"
                        event["tool_name"] = block.get("name")
                        event["tool_input"] = json.dumps(block.get("input", {}))
                        matched = True
                        break
                    elif block.get("type") == "thinking":
                        event["event_type"] = "thinking"
                        event["content"] = block.get("thinking", "")
                        matched = True
                        break
                    elif block.get("type") == "text":
                        event["event_type"] = "message"
                        event["content"] = block.get("text", "")
                        matched = True
                        break
                if not matched:
                    event["event_type"] = "message"
            else:
                event["event_type"] = "message"
        elif event_type == "user":
            # Claude Code sends tool results as type: "user" with tool_result content blocks
            event["event_type"] = "tool_result"
            event["role"] = "tool"
            msg_content = data.get("message", {}).get("content", []) if isinstance(data.get("message"), dict) else []
            if isinstance(msg_content, list):
                for block in msg_content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        event["tool_output"] = block.get("content", "")
                        if block.get("is_error"):
                            event["is_error"] = True
                        break
        elif event_type == "tool_use":
            event["tool_name"] = data.get("name")
            event["tool_input"] = json.dumps(data.get("input", {}))
        elif event_type == "tool_result":
            event["tool_output"] = self._extract_content(data) or ""
            if isinstance(event["tool_output"], str) and "error" in event["tool_output"].lower():
                event["is_error"] = True
        elif event_type == "result":
            event["content"] = self._extract_content(data)
            event["session_id"] = data.get("session_id")
            cost = data.get("total_cost_usd")
            if cost is not None:
                event["cost_usd"] = cost
            if data.get("is_error"):
                event["is_error"] = True

        return event

    def _extract_content(self, data: dict) -> str | None:
        # Handle content blocks (list of {type, text})
        content = data.get("content")
        if isinstance(content, list):
            texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
            return "\n".join(texts) if texts else None
        if isinstance(content, str):
            return content
        # Handle message wrapper
        message = data.get("message")
        if isinstance(message, dict):
            return self._extract_content(message)
        return None
