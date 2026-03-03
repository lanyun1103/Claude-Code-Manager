from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.task import Task


class TaskQueue:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Task:
        task = Task(**kwargs)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get(self, task_id: int) -> Task | None:
        return await self.db.get(Task, task_id)

    async def list_tasks(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[Task]:
        stmt = select(Task).order_by(Task.created_at.desc())
        if status:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_task(self, task_id: int, **kwargs) -> Task | None:
        task = await self.get(task_id)
        if not task:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(task, key, value)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task_id: int) -> bool:
        task = await self.get(task_id)
        if not task:
            return False
        if task.status not in ("pending", "failed", "cancelled", "conflict"):
            return False
        await self.db.delete(task)
        await self.db.commit()
        return True

    async def dequeue(self) -> Task | None:
        """Get the highest-priority pending task and mark it as in_progress."""
        stmt = (
            select(Task)
            .where(Task.status == "pending")
            .order_by(Task.priority.asc(), Task.created_at.asc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if task:
            task.status = "in_progress"
            task.started_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(task)
        return task

    async def mark_status(self, task_id: int, status: str, **extra) -> None:
        """Generic status update with optional extra fields."""
        values = {"status": status, **extra}
        if status in ("completed", "failed"):
            values.setdefault("completed_at", datetime.utcnow())
        await self.db.execute(
            update(Task).where(Task.id == task_id).values(**values)
        )
        await self.db.commit()

    async def mark_completed(self, task_id: int) -> None:
        await self.db.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(status="completed", completed_at=datetime.utcnow())
        )
        await self.db.commit()

    async def mark_failed(self, task_id: int, error: str) -> None:
        await self.db.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(status="failed", error_message=error, completed_at=datetime.utcnow())
        )
        await self.db.commit()

    async def retry(self, task_id: int) -> Task | None:
        task = await self.get(task_id)
        if not task:
            return None
        task.status = "pending"
        task.retry_count += 1
        task.error_message = None
        task.started_at = None
        task.completed_at = None
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def cancel(self, task_id: int) -> Task | None:
        task = await self.get(task_id)
        if not task or task.status not in ("pending", "in_progress", "executing", "merging"):
            return None
        task.status = "cancelled"
        task.completed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(task)
        return task
