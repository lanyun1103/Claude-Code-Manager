import re
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, inspect
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect the full target schema.
# New models must be imported here for autogenerate to work.
from backend.models.instance import Instance   # noqa: F401
from backend.models.project import Project     # noqa: F401
from backend.models.task import Task           # noqa: F401
from backend.models.log_entry import LogEntry  # noqa: F401
from backend.models.worktree import Worktree   # noqa: F401
from backend.database import Base

target_metadata = Base.metadata

# Override sqlalchemy.url from app settings.
# Convert async URL (sqlite+aiosqlite://...) to sync (sqlite://...) for Alembic.
from backend.config import settings
sync_url = re.sub(r'\+aiosqlite', '', settings.database_url)
config.set_main_option('sqlalchemy.url', sync_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # required for SQLite ALTER TABLE support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
