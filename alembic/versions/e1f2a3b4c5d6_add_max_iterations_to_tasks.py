"""add max_iterations to tasks

Revision ID: e1f2a3b4c5d6
Revises: 69d5cf74de62
Create Date: 2026-03-21 00:00:00.000000

Adds tasks.max_iterations — configurable upper bound on loop task iterations
(default 50). When a loop task reaches this limit it is automatically aborted
rather than running indefinitely.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = '69d5cf74de62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('max_iterations', sa.Integer(), nullable=False, server_default='50'))


def downgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('max_iterations')
