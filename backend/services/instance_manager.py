import asyncio
import os
import signal
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.instance import Instance
from backend.models.task import Task
from backend.models.log_entry import LogEntry
from backend.services.stream_parser import StreamParser
from backend.services.ws_broadcaster import WebSocketBroadcaster


class InstanceManager:
    """Manages multiple Claude Code subprocess instances."""

    def __init__(self, db_factory, broadcaster: WebSocketBroadcaster):
        self.db_factory = db_factory  # async_sessionmaker
        self.broadcaster = broadcaster
        self.parser = StreamParser()
        self.processes: dict[int, asyncio.subprocess.Process] = {}
        self._tasks: dict[int, asyncio.Task] = {}  # instance_id -> consumer task

    async def launch(self, instance_id: int, prompt: str, task_id: int | None = None, cwd: str | None = None, model: str | None = None, resume_session_id: str | None = None) -> int:
        """Launch a Claude Code subprocess for the given instance.

        If resume_session_id is provided, uses --resume to continue the conversation.
        """
        cmd = [
            settings.claude_binary,
            "-p", prompt,
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            "--verbose",
        ]
        if resume_session_id:
            cmd.extend(["--resume", resume_session_id])
        if model:
            cmd.extend(["--model", model])

        # Must unset CLAUDE_CODE env var to avoid nested session detection
        env = {k: v for k, v in os.environ.items() if k.upper() not in ("CLAUDECODE", "CLAUDE_CODE")}

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd or os.getcwd(),
            env=env,
        )

        self.processes[instance_id] = process

        # Update instance record
        async with self.db_factory() as db:
            await db.execute(
                update(Instance)
                .where(Instance.id == instance_id)
                .values(
                    pid=process.pid,
                    status="running",
                    current_task_id=task_id,
                    started_at=datetime.utcnow(),
                    last_heartbeat=datetime.utcnow(),
                )
            )
            # Save cwd to task for session resumption
            if task_id:
                actual_cwd = cwd or os.getcwd()
                await db.execute(
                    update(Task)
                    .where(Task.id == task_id)
                    .values(last_cwd=actual_cwd)
                )
            await db.commit()

        # Start consuming stdout
        consumer = asyncio.create_task(
            self._consume_output(instance_id, task_id, process)
        )
        self._tasks[instance_id] = consumer

        return process.pid

    async def _consume_output(self, instance_id: int, task_id: int | None, process: asyncio.subprocess.Process):
        """Read NDJSON lines from stdout, parse, store, and broadcast."""
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue

                events = self.parser.parse_line(text)
                if not events:
                    continue

                for event in events:
                    # Extract session_id and save to task
                    session_id = event.pop("session_id", None)
                    cost_usd = event.pop("cost_usd", None)
                    if session_id and task_id:
                        async with self.db_factory() as db:
                            await db.execute(
                                update(Task)
                                .where(Task.id == task_id)
                                .values(session_id=session_id)
                            )
                            await db.commit()
                    if cost_usd is not None:
                        async with self.db_factory() as db:
                            await db.execute(
                                update(Instance)
                                .where(Instance.id == instance_id)
                                .values(total_cost_usd=cost_usd)
                            )
                            await db.commit()

                    # Store in DB
                    async with self.db_factory() as db:
                        entry = LogEntry(
                            instance_id=instance_id,
                            task_id=task_id,
                            event_type=event["event_type"],
                            role=event.get("role"),
                            content=event.get("content"),
                            tool_name=event.get("tool_name"),
                            tool_input=event.get("tool_input"),
                            tool_output=event.get("tool_output"),
                            raw_json=event.get("raw_json"),
                            is_error=event.get("is_error", False),
                        )
                        db.add(entry)
                        await db.commit()

                        # Update heartbeat
                        await db.execute(
                            update(Instance)
                            .where(Instance.id == instance_id)
                            .values(last_heartbeat=datetime.utcnow())
                        )
                        await db.commit()

                    # Broadcast via WebSocket
                    broadcast_data = {k: v for k, v in event.items() if k != "raw_json"}
                    await self.broadcaster.broadcast(f"instance:{instance_id}", broadcast_data)
                    if task_id:
                        await self.broadcaster.broadcast(f"task:{task_id}", broadcast_data)

        except asyncio.CancelledError:
            pass
        finally:
            # Wait for process to finish
            await process.wait()
            exit_code = process.returncode

            # Read stderr
            stderr_data = await process.stderr.read()
            stderr_text = stderr_data.decode("utf-8", errors="replace").strip() if stderr_data else ""

            # Update instance status
            async with self.db_factory() as db:
                new_status = "idle" if exit_code == 0 else "error"
                values = {
                    "status": new_status,
                    "pid": None,
                    "current_task_id": None,
                }
                if exit_code == 0:
                    await db.execute(
                        update(Instance)
                        .where(Instance.id == instance_id)
                        .values(
                            **values,
                            total_tasks_completed=Instance.total_tasks_completed + 1,
                        )
                    )
                else:
                    await db.execute(
                        update(Instance).where(Instance.id == instance_id).values(**values)
                    )
                await db.commit()

            # Broadcast completion
            exit_event = {
                "event_type": "process_exit",
                "exit_code": exit_code,
                "stderr": stderr_text[:2000] if stderr_text else None,
            }
            await self.broadcaster.broadcast(f"instance:{instance_id}", exit_event)
            if task_id:
                await self.broadcaster.broadcast(f"task:{task_id}", exit_event)
            await self.broadcaster.broadcast("system", {
                "event": "instance_status",
                "instance_id": instance_id,
                "status": "idle" if exit_code == 0 else "error",
                "exit_code": exit_code,
            })

            self.processes.pop(instance_id, None)
            self._tasks.pop(instance_id, None)

    async def stop(self, instance_id: int) -> bool:
        """Stop a running Claude Code instance."""
        process = self.processes.get(instance_id)
        if not process or process.returncode is not None:
            return False

        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()

        # Cancel consumer task
        task = self._tasks.get(instance_id)
        if task and not task.done():
            task.cancel()

        async with self.db_factory() as db:
            await db.execute(
                update(Instance)
                .where(Instance.id == instance_id)
                .values(status="stopped", pid=None, current_task_id=None)
            )
            await db.commit()

        self.processes.pop(instance_id, None)
        return True

    def is_running(self, instance_id: int) -> bool:
        process = self.processes.get(instance_id)
        return process is not None and process.returncode is None
