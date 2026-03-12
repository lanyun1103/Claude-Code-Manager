"""add git config fields to projects

Revision ID: a1b2c3d4e5f6
Revises: 75caedb511e7
Create Date: 2026-03-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, tuple, None] = '0bac1f0f03d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('git_author_name', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('git_author_email', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('git_credential_type', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('git_ssh_key_path', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('git_https_username', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('git_https_token', sa.String(500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('git_https_token')
        batch_op.drop_column('git_https_username')
        batch_op.drop_column('git_ssh_key_path')
        batch_op.drop_column('git_credential_type')
        batch_op.drop_column('git_author_email')
        batch_op.drop_column('git_author_name')
