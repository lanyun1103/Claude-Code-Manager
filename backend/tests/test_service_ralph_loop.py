"""Tests for RalphLoop — only lifecycle management, not the full _loop body."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.services.ralph_loop import RalphLoop


def _make_ralph_loop():
    return RalphLoop(
        db_factory=MagicMock(),
        instance_manager=MagicMock(),
        broadcaster=MagicMock(),
    )


@pytest.mark.asyncio
async def test_start_creates_task():
    rl = _make_ralph_loop()
    # Patch _loop to be a simple coroutine that sleeps forever
    async def fake_loop(instance_id):
        await asyncio.sleep(999)

    rl._loop = fake_loop
    await rl.start(1)
    assert 1 in rl._loops
    assert not rl._loops[1].done()
    # Cleanup
    rl._loops[1].cancel()
    try:
        await rl._loops[1]
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_start_idempotent():
    rl = _make_ralph_loop()

    async def fake_loop(instance_id):
        await asyncio.sleep(999)

    rl._loop = fake_loop
    await rl.start(1)
    first_task = rl._loops[1]
    await rl.start(1)
    assert rl._loops[1] is first_task  # Same task, not replaced
    # Cleanup
    first_task.cancel()
    try:
        await first_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_stop_cancels():
    rl = _make_ralph_loop()

    async def fake_loop(instance_id):
        await asyncio.sleep(999)

    rl._loop = fake_loop
    await rl.start(1)
    task = rl._loops[1]
    await rl.stop(1)
    assert 1 not in rl._loops
    # Give event loop a tick for cancellation
    await asyncio.sleep(0)
    assert task.cancelled() or task.done()


@pytest.mark.asyncio
async def test_is_running_true():
    rl = _make_ralph_loop()

    async def fake_loop(instance_id):
        await asyncio.sleep(999)

    rl._loop = fake_loop
    await rl.start(1)
    assert rl.is_running(1) is True
    # Cleanup
    rl._loops[1].cancel()
    try:
        await rl._loops[1]
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_is_running_false():
    rl = _make_ralph_loop()
    assert rl.is_running(1) is False
    assert rl.is_running(999) is False
