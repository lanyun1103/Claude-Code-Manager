import logging
import subprocess
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings

logger = logging.getLogger(__name__)

# Project root (where alembic.ini lives)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Resolve relative SQLite paths against the project root so the engine always
# opens the correct database regardless of the process's working directory.
_db_url = settings.database_url
if _db_url.startswith("sqlite"):
    import re
    m = re.match(r"(sqlite\+?\w*:///)(\./.+)", _db_url)
    if m:
        _db_url = m.group(1) + str((_PROJECT_ROOT / m.group(2)).resolve())

engine = create_async_engine(_db_url, echo=False)
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

    Uses subprocess to run alembic to avoid deadlocks with uvicorn's event loop.
    """
    # Detect whether this is a legacy database (created before Alembic was introduced).
    async with engine.begin() as conn:
        def _check(sync_conn):
            inspector = inspect(sync_conn)
            tables = inspector.get_table_names()
            return 'tasks' in tables, 'alembic_version' in tables

        has_tables, has_alembic = await conn.run_sync(_check)

    # Dispose all pooled connections to avoid SQLite lock conflicts with alembic
    await engine.dispose()

    if has_tables and not has_alembic:
        # Legacy database: stamp initial revision, then upgrade
        result = subprocess.run(
            ["uv", "run", "alembic", "stamp", "6b3f8a1c2d9e"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("Alembic stamp failed: %s", result.stderr)
            raise RuntimeError(f"Alembic stamp failed: {result.stderr}")

    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=str(_PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("Alembic upgrade failed: %s", result.stderr)
        raise RuntimeError(f"Alembic upgrade failed: {result.stderr}")

    if result.stderr:
        # Log alembic migration info (it writes to stderr)
        for line in result.stderr.strip().splitlines():
            logger.info(line.strip())


async def get_db():
    async with async_session() as session:
        yield session
