import asyncio
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings

# Project root (where alembic.ini lives)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

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

    cfg = Config(str(_PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "alembic"))

    if has_tables and not has_alembic:
        # Legacy database (created before Alembic was introduced).
        # Stamp the initial schema revision, then upgrade to apply any new migrations.
        await asyncio.get_event_loop().run_in_executor(
            None, command.stamp, cfg, "6b3f8a1c2d9e"
        )
        await asyncio.get_event_loop().run_in_executor(
            None, command.upgrade, cfg, "head"
        )
    else:
        # Fresh install or already Alembic-tracked: apply any pending migrations.
        await asyncio.get_event_loop().run_in_executor(
            None, command.upgrade, cfg, "head"
        )


async def get_db():
    async with async_session() as session:
        yield session
