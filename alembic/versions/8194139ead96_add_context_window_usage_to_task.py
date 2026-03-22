"""add context_window_usage to task

Revision ID: 8194139ead96
Revises: e1f2a3b4c5d6
Create Date: 2026-03-22 06:07:49.342655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8194139ead96'
down_revision: Union[str, None] = '1042ddf2318a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('context_window_usage', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('context_window_usage')
