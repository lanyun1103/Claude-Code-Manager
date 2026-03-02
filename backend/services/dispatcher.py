import asyncio
import logging
from datetime import datetime

from sqlalchemy import select, update

from backend.config import settings
from backend.models.instance import Instance
from backend.models.task import Task
from backend.models.project import Project
from backend.services.instance_manager import InstanceManager
from backend.services.task_queue import TaskQueue
from backend.services.worktree_manager import WorktreeManager, WorktreeInfo
from backend.services.ws_broadcaster import WebSocketBroadcaster

logger = logging.getLogger(__name__)


class GlobalDispatcher:
    """Single global dispatcher that manages all instances and task lifecycle.

    Claude Code is fully autonomous — it handles commit, fetch, merge, push,
    and conflict resolution itself. The dispatcher only manages:
    - Task assignment (dequeue)
    - Worktree creation/cleanup
    - Starting/waiting on Claude Code processes
    - Marking tasks completed/failed
    """

    def __init__(
        self,
        db_factory,
        instance_manager: InstanceManager,
        worktree_manager: WorktreeManager,
        broadcaster: WebSocketBroadcaster,
    ):
        self.db_factory = db_factory
        self.instance_manager = instance_manager
        self.worktree_manager = worktree_manager
        self.broadcaster = broadcaster
        self._dispatch_task: asyncio.Task | None = None
        self._running_tasks: dict[int, asyncio.Task] = {}  # instance_id -> lifecycle task
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self):
        if self._running:
            return
        self._running = True

        # Ensure we have worker instances up to max_concurrent_instances
        await self._ensure_instances()

        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("GlobalDispatcher started")

    async def stop(self):
        self._running = False
        if self._dispatch_task and not self._dispatch_task.done():
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass

        # Cancel all running lifecycle tasks
        for instance_id, task in list(self._running_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._running_tasks.clear()
        logger.info("GlobalDispatcher stopped")

    def status(self) -> dict:
        return {
            "running": self._running,
            "active_tasks": {
                iid: not t.done() for iid, t in self._running_tasks.items()
            },
        }

    async def _ensure_instances(self):
        """Create worker instances in DB if fewer than max_concurrent_instances exist."""
        async with self.db_factory() as db:
            result = await db.execute(select(Instance))
            existing = list(result.scalars().all())

        needed = settings.max_concurrent_instances - len(existing)
        if needed > 0:
            async with self.db_factory() as db:
                for i in range(needed):
                    name = f"worker-{len(existing) + i + 1}"
                    instance = Instance(name=name, model=settings.default_model)
                    db.add(instance)
                await db.commit()
            logger.info(f"Created {needed} worker instances")

    async def _dispatch_loop(self):
        """Poll for idle instances + pending tasks and dispatch."""
        while self._running:
            try:
                # Find idle instances
                async with self.db_factory() as db:
                    result = await db.execute(
                        select(Instance).where(Instance.status.in_(["idle", "stopped"]))
                    )
                    idle_instances = list(result.scalars().all())

                for instance in idle_instances:
                    # Skip if already running a lifecycle
                    if instance.id in self._running_tasks and not self._running_tasks[instance.id].done():
                        continue

                    # Dequeue a task
                    async with self.db_factory() as db:
                        queue = TaskQueue(db)
                        task = await queue.dequeue()

                    if not task:
                        break  # No more tasks

                    # Resolve project -> target_repo
                    if task.project_id and not task.target_repo:
                        async with self.db_factory() as db:
                            project = await db.get(Project, task.project_id)
                            if project and project.local_path:
                                await db.execute(
                                    update(Task)
                                    .where(Task.id == task.id)
                                    .values(target_repo=project.local_path)
                                )
                                await db.commit()
                                task.target_repo = project.local_path

                    logger.info(f"Dispatching task {task.id} ({task.title}) to instance {instance.id} ({instance.name})")
                    self._running_tasks[instance.id] = asyncio.create_task(
                        self._run_task_lifecycle(instance.id, task)
                    )

                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dispatch loop error: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _run_task_lifecycle(self, instance_id: int, task: Task):
        """Execute the task lifecycle: assign → worktree → Claude Code → cleanup."""
        worktree: WorktreeInfo | None = None
        try:
            # === Step 1: Mark in_progress (already done by dequeue) ===
            await self.broadcaster.broadcast("tasks", {
                "event": "status_change",
                "task_id": task.id,
                "old_status": "pending",
                "new_status": "in_progress",
                "instance_id": instance_id,
            })

            # === Step 2: Create workspace ===
            cwd = task.target_repo or "."
            branch_name = f"task-{task.id}-{task.title[:20].replace(' ', '-').lower()}"
            base_branch = task.target_branch or "main"

            try:
                worktree = await self.worktree_manager.create(
                    repo_path=cwd,
                    branch_name=branch_name,
                    base_branch=base_branch,
                    instance_id=instance_id,
                )
                cwd = worktree.path

                async with self.db_factory() as db:
                    await db.execute(
                        update(Task)
                        .where(Task.id == task.id)
                        .values(result_branch=branch_name, instance_id=instance_id)
                    )
                    await db.commit()
            except RuntimeError as e:
                logger.warning(f"Worktree creation failed, using repo directly: {e}")
                async with self.db_factory() as db:
                    await db.execute(
                        update(Task)
                        .where(Task.id == task.id)
                        .values(instance_id=instance_id)
                    )
                    await db.commit()

            # === Step 3: Execute (Claude Code — fully autonomous) ===
            async with self.db_factory() as db:
                await db.execute(
                    update(Task).where(Task.id == task.id).values(status="executing")
                )
                await db.commit()
            await self.broadcaster.broadcast("tasks", {
                "event": "status_change",
                "task_id": task.id,
                "new_status": "executing",
                "instance_id": instance_id,
            })

            # Plan mode handling
            if task.mode == "plan" and not task.plan_approved:
                await self._run_plan_phase(instance_id, task, cwd)
                return  # Wait for plan approval, task goes back to pending

            # Build prompt with worktree context
            full_prompt = f"""你正在 worktree 分支 `{branch_name}` 中工作，基于 `{base_branch}`。
请阅读项目根目录的 CLAUDE.md 了解项目规范和任务完成后的 git 流程。

任务:
{task.description}"""

            await self.instance_manager.launch(
                instance_id=instance_id,
                prompt=full_prompt,
                task_id=task.id,
                cwd=cwd,
                model=None,
            )

            # Wait for process to finish
            process = self.instance_manager.processes.get(instance_id)
            if process:
                await process.wait()

            exit_code = process.returncode if process else -1

            if exit_code != 0:
                # Execution failed — retry or mark failed
                async with self.db_factory() as db:
                    queue = TaskQueue(db)
                    t = await queue.get(task.id)
                    if t and t.retry_count < t.max_retries:
                        await queue.retry(task.id)
                        status = "pending"
                    else:
                        await queue.mark_failed(task.id, f"Exit code: {exit_code}")
                        status = "failed"

                await self.broadcaster.broadcast("tasks", {
                    "event": "status_change",
                    "task_id": task.id,
                    "new_status": status,
                    "instance_id": instance_id,
                })

                if worktree:
                    await self.worktree_manager.remove(worktree)
                return

            # === Claude Code completed successfully ===
            # (Claude Code handles commit, merge, push autonomously)

            # Mark completed
            async with self.db_factory() as db:
                queue = TaskQueue(db)
                await queue.mark_completed(task.id)

            await self.broadcaster.broadcast("tasks", {
                "event": "status_change",
                "task_id": task.id,
                "new_status": "completed",
                "instance_id": instance_id,
            })

            # Keep worktree alive so chat can --resume with the same cwd.
            # Worktrees are cleaned up only on failure/exception or manual delete.

            # Update instance stats
            async with self.db_factory() as db:
                await db.execute(
                    update(Instance)
                    .where(Instance.id == instance_id)
                    .values(total_tasks_completed=Instance.total_tasks_completed + 1)
                )
                await db.commit()

            logger.info(f"Task {task.id} ({task.title}) completed successfully on instance {instance_id}")

        except asyncio.CancelledError:
            logger.info(f"Lifecycle cancelled for task {task.id} on instance {instance_id}")
            raise
        except Exception as e:
            logger.error(f"Lifecycle error for task {task.id}: {e}", exc_info=True)
            async with self.db_factory() as db:
                queue = TaskQueue(db)
                await queue.mark_failed(task.id, str(e)[:500])
            await self.broadcaster.broadcast("tasks", {
                "event": "status_change",
                "task_id": task.id,
                "new_status": "failed",
                "instance_id": instance_id,
            })
            if worktree:
                try:
                    await self.worktree_manager.remove(worktree)
                except Exception:
                    pass
        finally:
            self._running_tasks.pop(instance_id, None)

    async def _run_plan_phase(self, instance_id: int, task: Task, cwd: str):
        """Run plan phase for plan-mode tasks."""
        plan_prompt = (
            f"Please analyze the following task and create a detailed plan. "
            f"Do NOT execute any changes, only describe what you would do:\n\n{task.description}"
        )
        await self.instance_manager.launch(
            instance_id=instance_id,
            prompt=plan_prompt,
            task_id=task.id,
            cwd=cwd,
            model=None,
        )
        process = self.instance_manager.processes.get(instance_id)
        if process:
            await process.wait()

        # Collect plan content from logs
        async with self.db_factory() as db:
            from sqlalchemy import select as sa_select
            from backend.models.log_entry import LogEntry
            result = await db.execute(
                sa_select(LogEntry.content)
                .where(
                    LogEntry.task_id == task.id,
                    LogEntry.event_type == "message",
                    LogEntry.role == "assistant",
                )
                .order_by(LogEntry.id)
            )
            plan_texts = [r[0] for r in result.all() if r[0]]
            plan_content = "\n".join(plan_texts)

            await db.execute(
                update(Task)
                .where(Task.id == task.id)
                .values(plan_content=plan_content, status="plan_review")
            )
            await db.commit()

        await self.broadcaster.broadcast("tasks", {
            "event": "plan_ready",
            "task_id": task.id,
            "instance_id": instance_id,
        })
