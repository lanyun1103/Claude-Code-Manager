"""Tests for StreamParser — NDJSON line parsing."""
import json
import pytest

from backend.services.stream_parser import StreamParser


@pytest.fixture
def parser():
    return StreamParser()


def test_empty_line(parser):
    assert parser.parse_line("") is None
    assert parser.parse_line("   ") is None


def test_invalid_json(parser):
    result = parser.parse_line("not json at all")
    assert result is not None
    assert result["event_type"] == "parse_error"
    assert result["is_error"] is True
    assert result["content"] == "not json at all"


def test_system_init(parser):
    line = json.dumps({
        "type": "system",
        "subtype": "init",
        "session_id": "abc-123",
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "system_init"
    assert result["session_id"] == "abc-123"


def test_assistant_message(parser):
    line = json.dumps({
        "type": "assistant",
        "content": [{"type": "text", "text": "Hello world"}],
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "message"
    assert result["role"] == "assistant"
    assert result["content"] == "Hello world"


def test_tool_use(parser):
    line = json.dumps({
        "type": "tool_use",
        "name": "Read",
        "input": {"file_path": "/tmp/test.py"},
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "tool_use"
    assert result["tool_name"] == "Read"
    assert '"file_path"' in result["tool_input"]


def test_tool_result(parser):
    line = json.dumps({
        "type": "tool_result",
        "content": "file contents here",
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "tool_result"
    assert result["tool_output"] == "file contents here"
    assert result["is_error"] is False


def test_tool_result_error(parser):
    line = json.dumps({
        "type": "tool_result",
        "content": "Error: file not found",
    })
    result = parser.parse_line(line)
    assert result["is_error"] is True


def test_result_with_cost(parser):
    line = json.dumps({
        "type": "result",
        "session_id": "sess-456",
        "total_cost_usd": 0.42,
        "content": [{"type": "text", "text": "Done"}],
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "result"
    assert result["session_id"] == "sess-456"
    assert result["cost_usd"] == 0.42
    assert result["content"] == "Done"


def test_result_is_error(parser):
    line = json.dumps({
        "type": "result",
        "is_error": True,
        "content": "Something failed",
    })
    result = parser.parse_line(line)
    assert result["is_error"] is True


def test_content_extraction_string(parser):
    line = json.dumps({"type": "unknown", "content": "plain string"})
    result = parser.parse_line(line)
    assert result["content"] == "plain string"


def test_content_extraction_list(parser):
    line = json.dumps({
        "type": "unknown",
        "content": [
            {"type": "text", "text": "line 1"},
            {"type": "text", "text": "line 2"},
        ],
    })
    result = parser.parse_line(line)
    assert result["content"] == "line 1\nline 2"


def test_content_extraction_empty_list(parser):
    line = json.dumps({"type": "unknown", "content": []})
    result = parser.parse_line(line)
    assert result["content"] is None


def test_content_extraction_message_wrapper(parser):
    line = json.dumps({
        "type": "unknown",
        "message": {"content": [{"type": "text", "text": "nested"}]},
    })
    result = parser.parse_line(line)
    assert result["content"] == "nested"


def test_assistant_tool_use_block(parser):
    """assistant event with tool_use content block → tool_use event."""
    line = json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "toolu_123", "name": "Bash", "input": {"command": "ls -la"}}],
        },
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "tool_use"
    assert result["tool_name"] == "Bash"
    assert '"command"' in result["tool_input"]
    assert result["role"] == "assistant"


def test_assistant_thinking_block(parser):
    """assistant event with thinking content block → thinking event."""
    line = json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "thinking", "thinking": "Let me analyze this..."}],
        },
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "thinking"
    assert result["content"] == "Let me analyze this..."
    assert result["role"] == "assistant"


def test_user_event_tool_result(parser):
    """type: 'user' event with tool_result content → tool_result event."""
    line = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "toolu_123", "content": "file contents here", "is_error": False}],
        },
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "tool_result"
    assert result["role"] == "tool"
    assert result["tool_output"] == "file contents here"
    assert result["is_error"] is False


def test_user_event_tool_result_error(parser):
    """type: 'user' event with is_error flag → is_error set."""
    line = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "toolu_456", "content": "Error: not found", "is_error": True}],
        },
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "tool_result"
    assert result["is_error"] is True


def test_system_non_init(parser):
    """system event with non-init subtype → system_event."""
    line = json.dumps({
        "type": "system",
        "subtype": "task_started",
        "task_id": "abc",
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "system_event"
    assert result["content"] == "task_started"


def test_assistant_empty_content_blocks(parser):
    """assistant event with empty content blocks → message event."""
    line = json.dumps({
        "type": "assistant",
        "message": {"role": "assistant", "content": []},
    })
    result = parser.parse_line(line)
    assert result["event_type"] == "message"
