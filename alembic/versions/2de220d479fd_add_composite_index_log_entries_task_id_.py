"""add composite index log_entries task_id id

Revision ID: 2de220d479fd
Revises: c4d7e2f9a0b1
Create Date: 2026-03-07 06:22:26.404805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2de220d479fd'
down_revision: Union[str, None] = 'c4d7e2f9a0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_log_entries_task_id_id', 'log_entries', ['task_id', 'id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_log_entries_task_id_id', table_name='log_entries')
