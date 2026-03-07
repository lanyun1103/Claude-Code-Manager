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
    # Use batch mode because SQLite does not support ALTER COLUMN natively.
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('todo_file_path', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('loop_progress', sa.String(length=200), nullable=True))
        batch_op.alter_column('description', existing_type=sa.Text(), nullable=True)

    with op.batch_alter_table('log_entries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('loop_iteration', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('log_entries', schema=None) as batch_op:
        batch_op.drop_column('loop_iteration')

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.alter_column('description', existing_type=sa.Text(), nullable=False)
        batch_op.drop_column('loop_progress')
        batch_op.drop_column('todo_file_path')
