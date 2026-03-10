"""add show_in_selector to projects

Revision ID: 75caedb511e7
Revises: c4d7e2f9a0b1
Create Date: 2026-03-10 06:31:07.779419

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75caedb511e7'
down_revision: Union[str, None] = 'c4d7e2f9a0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('show_in_selector', sa.Boolean(), server_default='1', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('show_in_selector')
