"""add archived field to tasks

Revision ID: 492f4274adbb
Revises: b2c3d4e5f6a7
Create Date: 2026-03-13 04:02:41.513445

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '492f4274adbb'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('archived', sa.Boolean(), server_default='0', nullable=False))
        batch_op.create_index(batch_op.f('ix_tasks_archived'), ['archived'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tasks_archived'))
        batch_op.drop_column('archived')
