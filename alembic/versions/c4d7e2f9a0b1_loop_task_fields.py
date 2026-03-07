"""Loop task fields

Revision ID: c4d7e2f9a0b1
Revises: 6b3f8a1c2d9e
Create Date: 2026-03-07 00:00:00.000000

Adds support for the Loop task mode:
  - tasks.todo_file_path  — path to the todo list file (loop tasks only)
  - tasks.loop_progress   — Claude's self-reported progress string, e.g. "3/5"
  - tasks.description     — relaxed to nullable (loop tasks may omit description)
  - log_entries.loop_iteration — which iteration of a loop task produced this log entry
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c4d7e2f9a0b1'
down_revision: Union[str, None] = '6b3f8a1c2d9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite supports ADD COLUMN directly; avoid batch mode to prevent
    # CircularDependencyError in SQLAlchemy's topological sort.
    op.add_column('tasks', sa.Column('todo_file_path', sa.String(length=500), nullable=True))
    op.add_column('tasks', sa.Column('loop_progress', sa.String(length=200), nullable=True))
    # SQLite cannot ALTER COLUMN, but description is already TEXT and we only
    # relax nullability — SQLite doesn't enforce NOT NULL on existing rows anyway,
    # so this is a no-op at the DB level.

    op.add_column('log_entries', sa.Column('loop_iteration', sa.Integer(), nullable=True))


def downgrade() -> None:
    # SQLite doesn't support DROP COLUMN in older versions; use batch mode.
    with op.batch_alter_table('log_entries', schema=None) as batch_op:
        batch_op.drop_column('loop_iteration')

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('loop_progress')
        batch_op.drop_column('todo_file_path')
