"""add sort_order and tags to projects

Revision ID: 69d5cf74de62
Revises: 4236103a2c1c
Create Date: 2026-03-20 00:27:46.534760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69d5cf74de62'
down_revision: Union[str, None] = '4236103a2c1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('tags', sa.JSON(), server_default='[]', nullable=False))
        batch_op.create_index(batch_op.f('ix_projects_sort_order'), ['sort_order'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_projects_sort_order'))
        batch_op.drop_column('tags')
        batch_op.drop_column('sort_order')
