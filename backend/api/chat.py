import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.instance import Instance
from backend.models.task import Task
from backend.models.log_entry import LogEntry

router = APIRouter(prefix="/api/tasks", tags=["chat"])


class ChatMessage(BaseModel):
    message: str


async def _find_idle_instance(db: AsyncSession) -> Instance | None:
    """Find an idle instance to run a chat message."""
    result = await db.execute(
        select(Instance).where(Instance.status == "idle").order_by(Instance.id).limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/{task_id}/chat")
async def send_chat_message(
    task_id: int,
    body: ChatMessage,
    db: AsyncSession = Depends(get_db),
):
    """Send a follow-up message on a task, resuming its previous session."""
    from backend.main import instance_manager

    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not task.session_id:
        raise HTTPException(400, "No previous session on this task. Run the task first.")

    # Check no instance is currently working on this task
    for inst_id, proc in instance_manager.processes.items():
        if proc.returncode is None:
            inst = await db.get(Instance, inst_id)
            if inst and inst.current_task_id == task_id:
                raise HTTPException(400, "Task is currently being processed. Wait for it to finish.")

    # Find an idle instance
    inst = await _find_idle_instance(db)
    if not inst:
        raise HTTPException(400, "No idle instance available. Create one or wait.")

    # Store user message as a log entry
    user_log = LogEntry(
        instance_id=inst.id,
        task_id=task_id,
        event_type="user_message",
        role="user",
        content=body.message,
        is_error=False,
    )
    db.add(user_log)
    await db.commit()

    # Broadcast user message to task channel
    from backend.main import broadcaster
    await broadcaster.broadcast(f"task:{task_id}", {
        "event_type": "user_message",
        "role": "user",
        "content": body.message,
    })

    # Determine cwd: Claude Code launches in repo root, session binds there
    cwd = task.last_cwd or task.target_repo
    if not cwd or not os.path.isdir(cwd):
        raise HTTPException(400, "Task working directory not found.")

    # Launch with --resume, using the task's cwd
    pid = await instance_manager.launch(
        instance_id=inst.id,
        prompt=body.message,
        task_id=task_id,
        cwd=cwd,
        model=inst.model,
        resume_session_id=task.session_id,
    )
    return {"ok": True, "pid": pid, "instance_id": inst.id, "session_id": task.session_id}


@router.get("/{task_id}/chat/history")
async def get_chat_history(
    task_id: int,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
):
    """Get chat-formatted history for a task (user messages + assistant responses)."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    # Fetch the most recent N messages (desc) then reverse to chronological order
    stmt = (
        select(LogEntry)
        .where(
            LogEntry.task_id == task_id,
            LogEntry.event_type.in_(["user_message", "message", "result", "tool_use", "tool_result", "system_init", "system_event", "thinking", "process_exit"]),
        )
        .order_by(LogEntry.id.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    entries = list(reversed(result.scalars().all()))

    messages = []
    for entry in entries:
        # Skip heartbeat events
        if entry.event_type == "system_event" and entry.content == "task_progress":
            continue
        messages.append({
            "id": entry.id,
            "role": entry.role or ("assistant" if entry.event_type in ("message", "result") else "system"),
            "event_type": entry.event_type,
            "content": entry.content,
            "tool_name": entry.tool_name,
            "tool_input": entry.tool_input,
            "tool_output": entry.tool_output,
            "is_error": entry.is_error,
            "loop_iteration": entry.loop_iteration,
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        })

    return messages
