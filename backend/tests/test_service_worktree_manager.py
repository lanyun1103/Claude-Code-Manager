"""Tests for WorktreeManager — git worktree operations."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

from backend.services.worktree_manager import WorktreeManager, WorktreeInfo
from backend.models.worktree import Worktree as WorktreeModel


def _make_git_mock(success_commands=None, fail_commands=None):
    """Create a mock for _git that succeeds or fails based on command.

    success_commands: list of arg patterns that succeed (default: all succeed)
    fail_commands: list of arg patterns that raise RuntimeError
    """
    fail_commands = fail_commands or []

    async def mock_git(cwd, args):
        for pattern in fail_commands:
            if pattern in args or (isinstance(pattern, str) and pattern in " ".join(args)):
                raise RuntimeError(f"git {' '.join(args)} failed: mock error")
        return "mock output"

    return mock_git


@pytest.mark.asyncio
async def test_create_success(db_factory):
    """create() calls correct git commands and saves DB record."""
    wm = WorktreeManager(db_factory)

    with patch.object(wm, "_git", new_callable=AsyncMock, return_value="ok") as mock_git, \
         patch("backend.services.worktree_manager.os.makedirs"):
        info = await wm.create(
            repo_path="/repo",
            branch_name="task-1",
            base_branch="main",
            instance_id=1,
        )

    assert info.branch_name == "task-1"
    assert info.base_branch == "main"
    assert info.repo_path == "/repo"
    assert info.db_id is not None

    # Verify git commands: fetch, rev-parse, worktree add
    assert mock_git.await_count == 3

    # Verify DB record
    async with db_factory() as db:
        record = await db.get(WorktreeModel, info.db_id)
        assert record is not None
        assert record.branch_name == "task-1"
        assert record.status == "active"


@pytest.mark.asyncio
async def test_create_fetch_fails_continues(db_factory):
    """If git fetch origin fails, continues with local branch."""
    wm = WorktreeManager(db_factory)
    call_count = 0

    async def selective_git(cwd, args):
        nonlocal call_count
        call_count += 1
        if args == ["fetch", "origin"]:
            raise RuntimeError("network error")
        return "ok"

    with patch.object(wm, "_git", side_effect=selective_git), \
         patch("backend.services.worktree_manager.os.makedirs"):
        info = await wm.create(
            repo_path="/repo", branch_name="task-2", base_branch="main",
        )

    assert info.branch_name == "task-2"
    assert info.db_id is not None


@pytest.mark.asyncio
async def test_create_origin_branch_missing_fallback(db_factory):
    """If origin/main not found, falls back to local 'main'."""
    wm = WorktreeManager(db_factory)

    async def selective_git(cwd, args):
        if "rev-parse" in args:
            raise RuntimeError("not found")
        return "ok"

    with patch.object(wm, "_git", side_effect=selective_git), \
         patch("backend.services.worktree_manager.os.makedirs"):
        info = await wm.create(
            repo_path="/repo", branch_name="task-3", base_branch="main",
        )

    assert info.branch_name == "task-3"


@pytest.mark.asyncio
async def test_sync_latest_success(db_factory):
    """sync_latest fetches and merges, returns 'ok'."""
    wm = WorktreeManager(db_factory)
    with patch.object(wm, "_git", new_callable=AsyncMock, return_value="ok"):
        result = await wm.sync_latest("/wt/path", "main")
    assert result == "ok"


@pytest.mark.asyncio
async def test_sync_latest_conflict(db_factory):
    """sync_latest merge fails, aborts, returns 'conflict'."""
    wm = WorktreeManager(db_factory)

    async def selective_git(cwd, args):
        if "merge" in args and "--abort" not in args:
            raise RuntimeError("conflict")
        return "ok"

    with patch.object(wm, "_git", side_effect=selective_git):
        result = await wm.sync_latest("/wt/path", "main")
    assert result == "conflict"


@pytest.mark.asyncio
async def test_merge_to_main_success(db_factory):
    """merge_to_main rebases, checkouts, merges, pushes, returns 'merged'."""
    wm = WorktreeManager(db_factory)

    # Create a worktree record in DB
    async with db_factory() as db:
        record = WorktreeModel(
            repo_path="/repo", worktree_path="/wt/task-1",
            branch_name="task-1", base_branch="main",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        db_id = record.id

    worktree = WorktreeInfo(
        path="/wt/task-1", branch_name="task-1",
        base_branch="main", repo_path="/repo", db_id=db_id,
    )

    with patch.object(wm, "_git", new_callable=AsyncMock, return_value="ok"):
        result = await wm.merge_to_main(worktree)

    assert result == "merged"

    # Verify DB updated to "merged"
    async with db_factory() as db:
        record = await db.get(WorktreeModel, db_id)
        assert record.status == "merged"


@pytest.mark.asyncio
async def test_merge_to_main_conflict(db_factory):
    """merge_to_main rebase fails, returns 'conflict'."""
    wm = WorktreeManager(db_factory)
    worktree = WorktreeInfo(
        path="/wt/task-1", branch_name="task-1",
        base_branch="main", repo_path="/repo",
    )

    async def selective_git(cwd, args):
        if "rebase" in args and "--abort" not in args:
            raise RuntimeError("conflict during rebase")
        return "ok"

    with patch.object(wm, "_git", side_effect=selective_git):
        result = await wm.merge_to_main(worktree)
    assert result == "conflict"


@pytest.mark.asyncio
async def test_remove_worktree(db_factory):
    """remove() calls git worktree remove + branch -D, updates DB."""
    wm = WorktreeManager(db_factory)

    # Create DB record
    async with db_factory() as db:
        record = WorktreeModel(
            repo_path="/repo", worktree_path="/wt/task-rm",
            branch_name="task-rm", base_branch="main",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        db_id = record.id

    worktree = WorktreeInfo(
        path="/wt/task-rm", branch_name="task-rm",
        base_branch="main", repo_path="/repo", db_id=db_id,
    )

    with patch.object(wm, "_git", new_callable=AsyncMock, return_value="ok"):
        await wm.remove(worktree)

    async with db_factory() as db:
        record = await db.get(WorktreeModel, db_id)
        assert record.status == "removed"
        assert record.removed_at is not None
