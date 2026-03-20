"""add starred field to tasks

Revision ID: 4236103a2c1c
Revises: 17ce8c298139
Create Date: 2026-03-19 02:14:34.038878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4236103a2c1c'
down_revision: Union[str, None] = '17ce8c298139'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('starred', sa.Boolean(), server_default='0', nullable=False))
        batch_op.create_index(batch_op.f('ix_tasks_starred'), ['starred'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tasks_starred'))
        batch_op.drop_column('starred')
