import asyncio

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Apply all pending Alembic migrations.

    Behaviour:
    - Fresh install (no DB file): runs all migrations from scratch, creating every table.
    - Legacy DB (tables exist but no alembic_version table): stamps as head so Alembic
      knows the schema is already current, then handles future migrations normally.
    - Already tracked DB: runs any pending migrations and is otherwise a no-op.
    """
    from alembic.config import Config
    from alembic import command

    # Detect whether this is a legacy database (created before Alembic was introduced).
    async with engine.begin() as conn:
        def _check(sync_conn):
            inspector = inspect(sync_conn)
            tables = inspector.get_table_names()
            return 'tasks' in tables, 'alembic_version' in tables

        has_tables, has_alembic = await conn.run_sync(_check)

    cfg = Config("alembic.ini")

    if has_tables and not has_alembic:
        # Legacy database: all schema changes were applied via manual ALTER TABLE.
        # Stamp as head so Alembic treats it as fully up-to-date.
        await asyncio.get_event_loop().run_in_executor(None, command.stamp, cfg, "head")
    else:
        # Fresh install or already Alembic-tracked: apply any pending migrations.
        await asyncio.get_event_loop().run_in_executor(None, command.upgrade, cfg, "head")


async def get_db():
    async with async_session() as session:
        yield session
