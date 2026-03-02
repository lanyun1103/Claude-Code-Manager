"""Tests for Chat and Plan API endpoints."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.task import Task
from backend.models.instance import Instance


# === Chat tests ===


@pytest.mark.asyncio
async def test_chat_history_not_found(client):
    resp = await client.get("/api/tasks/9999/chat/history")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_history_empty(client):
    create_resp = await client.post("/api/tasks", json={
        "title": "T", "description": "d", "target_repo": "/tmp",
    })
    task_id = create_resp.json()["id"]
    resp = await client.get(f"/api/tasks/{task_id}/chat/history")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_chat_history_returns_tool_fields(client, session_factory):
    """Chat history should include tool_input and tool_output fields."""
    # Create a task
    create_resp = await client.post("/api/tasks", json={
        "title": "T", "description": "d", "target_repo": "/tmp",
    })
    task_id = create_resp.json()["id"]

    # Insert log entries with tool_input/tool_output directly in DB
    from backend.models.log_entry import LogEntry
    async with session_factory() as db:
        # tool_use entry
        db.add(LogEntry(
            instance_id=1,
            task_id=task_id,
            event_type="tool_use",
            role="assistant",
            tool_name="Edit",
            tool_input='{"file_path": "/tmp/test.py", "old_string": "foo", "new_string": "bar"}',
            is_error=False,
        ))
        # tool_result entry
        db.add(LogEntry(
            instance_id=1,
            task_id=task_id,
            event_type="tool_result",
            role="assistant",
            tool_name="Edit",
            tool_output="File updated successfully",
            is_error=False,
        ))
        await db.commit()

    resp = await client.get(f"/api/tasks/{task_id}/chat/history")
    assert resp.status_code == 200
    msgs = resp.json()
    assert len(msgs) == 2

    # tool_use should have tool_input
    assert msgs[0]["event_type"] == "tool_use"
    assert msgs[0]["tool_name"] == "Edit"
    assert msgs[0]["tool_input"] is not None
    assert "file_path" in msgs[0]["tool_input"]

    # tool_result should have tool_output
    assert msgs[1]["event_type"] == "tool_result"
    assert msgs[1]["tool_output"] == "File updated successfully"


@pytest.mark.asyncio
async def test_chat_send_no_session(client):
    """Sending chat to a task with no session should return 400."""
    create_resp = await client.post("/api/tasks", json={
        "title": "T", "description": "d", "target_repo": "/tmp",
    })
    task_id = create_resp.json()["id"]
    resp = await client.post(f"/api/tasks/{task_id}/chat", json={"message": "hello"})
    assert resp.status_code == 400
    assert "session" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_send_task_not_found(client):
    resp = await client.post("/api/tasks/9999/chat", json={"message": "hello"})
    assert resp.status_code == 404


# === Plan tests ===


@pytest.mark.asyncio
async def test_plan_approve_not_plan_review(client):
    """Approving a task not in plan_review state should return 400."""
    create_resp = await client.post("/api/tasks", json={
        "title": "T", "description": "d", "target_repo": "/tmp",
    })
    task_id = create_resp.json()["id"]
    resp = await client.post(f"/api/tasks/{task_id}/plan/approve")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_plan_reject_not_plan_review(client):
    """Rejecting a task not in plan_review state should return 400."""
    create_resp = await client.post("/api/tasks", json={
        "title": "T", "description": "d", "target_repo": "/tmp",
    })
    task_id = create_resp.json()["id"]
    resp = await client.post(f"/api/tasks/{task_id}/plan/reject")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_plan_approve_success(client, session_factory):
    """Approving a plan-mode task in plan_review state should succeed."""
    create_resp = await client.post("/api/tasks", json={
        "title": "Plan Task", "description": "d", "target_repo": "/tmp", "mode": "plan",
    })
    task_id = create_resp.json()["id"]

    # Set task to plan_review state directly in DB
    async with session_factory() as db:
        await db.execute(
            update(Task).where(Task.id == task_id).values(
                status="plan_review", plan_content="Here is my plan..."
            )
        )
        await db.commit()

    resp = await client.post(f"/api/tasks/{task_id}/plan/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["plan_approved"] is True


@pytest.mark.asyncio
async def test_plan_reject_success(client, session_factory):
    """Rejecting a plan-mode task in plan_review state should cancel it."""
    create_resp = await client.post("/api/tasks", json={
        "title": "Plan Task", "description": "d", "target_repo": "/tmp", "mode": "plan",
    })
    task_id = create_resp.json()["id"]

    async with session_factory() as db:
        await db.execute(
            update(Task).where(Task.id == task_id).values(
                status="plan_review", plan_content="Here is my plan..."
            )
        )
        await db.commit()

    resp = await client.post(f"/api/tasks/{task_id}/plan/reject")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["plan_approved"] is False


@pytest.mark.asyncio
async def test_plan_approve_not_found(client):
    resp = await client.post("/api/tasks/9999/plan/approve")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_plan_reject_not_found(client):
    resp = await client.post("/api/tasks/9999/plan/reject")
    assert resp.status_code == 404


# === Chat send extra tests ===


async def _create_task_with_session(client, session_factory, **extra_fields):
    """Helper: create a task and set session_id + target_repo in DB."""
    create_resp = await client.post("/api/tasks", json={
        "title": "Chat Task", "description": "d", "target_repo": "/tmp",
    })
    task_id = create_resp.json()["id"]
    values = {"session_id": "test-session-123", **extra_fields}
    async with session_factory() as db:
        await db.execute(update(Task).where(Task.id == task_id).values(**values))
        await db.commit()
    return task_id


@pytest.mark.asyncio
async def test_chat_send_no_idle_instance(client, session_factory):
    """Task has session but no idle instances exist."""
    task_id = await _create_task_with_session(client, session_factory)

    mock_im = MagicMock()
    mock_im.processes = {}
    mock_broadcaster = MagicMock()
    mock_broadcaster.broadcast = AsyncMock()

    with patch("backend.main.instance_manager", mock_im), \
         patch("backend.main.broadcaster", mock_broadcaster):
        resp = await client.post(f"/api/tasks/{task_id}/chat", json={"message": "hi"})
    assert resp.status_code == 400
    assert "no idle instance" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_send_task_being_processed(client, session_factory):
    """Task has session but an instance is currently processing it."""
    task_id = await _create_task_with_session(client, session_factory)

    # Create an instance that's "running" this task
    async with session_factory() as db:
        inst = Instance(name="busy-inst", status="idle", current_task_id=task_id)
        db.add(inst)
        await db.commit()
        await db.refresh(inst)
        inst_id = inst.id

    # Mock a process with returncode=None (still running) for this instance
    mock_proc = MagicMock()
    mock_proc.returncode = None
    mock_im = MagicMock()
    mock_im.processes = {inst_id: mock_proc}

    with patch("backend.main.instance_manager", mock_im):
        resp = await client.post(f"/api/tasks/{task_id}/chat", json={"message": "hi"})
    assert resp.status_code == 400
    assert "currently being processed" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_send_cwd_uses_last_cwd(client, session_factory):
    """When last_cwd exists, uses it as cwd."""
    task_id = await _create_task_with_session(
        client, session_factory,
        last_cwd="/tmp",  # /tmp exists
    )

    # Create an idle instance
    async with session_factory() as db:
        inst = Instance(name="idle-inst", status="idle")
        db.add(inst)
        await db.commit()

    mock_im = MagicMock()
    mock_im.processes = {}
    mock_im.launch = AsyncMock(return_value=42)
    mock_broadcaster = MagicMock()
    mock_broadcaster.broadcast = AsyncMock()

    with patch("backend.main.instance_manager", mock_im), \
         patch("backend.main.broadcaster", mock_broadcaster):
        resp = await client.post(f"/api/tasks/{task_id}/chat", json={"message": "followup"})
    assert resp.status_code == 200
    mock_im.launch.assert_awaited_once()
    call_kwargs = mock_im.launch.call_args
    assert call_kwargs.kwargs.get("cwd") == "/tmp" or call_kwargs[1].get("cwd") == "/tmp"


@pytest.mark.asyncio
async def test_chat_send_cwd_not_found(client, session_factory):
    """When cwd doesn't exist -> 400."""
    task_id = await _create_task_with_session(
        client, session_factory,
        last_cwd="/nonexistent/a",
    )

    # Create an idle instance
    async with session_factory() as db:
        inst = Instance(name="idle-inst-2", status="idle")
        db.add(inst)
        await db.commit()

    mock_im = MagicMock()
    mock_im.processes = {}
    mock_broadcaster = MagicMock()
    mock_broadcaster.broadcast = AsyncMock()

    with patch("backend.main.instance_manager", mock_im), \
         patch("backend.main.broadcaster", mock_broadcaster):
        resp = await client.post(f"/api/tasks/{task_id}/chat", json={"message": "hi"})
    assert resp.status_code == 400
    assert "directory" in resp.json()["detail"].lower()
