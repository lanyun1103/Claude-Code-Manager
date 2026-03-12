"""add global_settings table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, tuple, None] = ('a1b2c3d4e5f6', '0bac1f0f03d6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'global_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('git_author_name', sa.String(200), nullable=True),
        sa.Column('git_author_email', sa.String(200), nullable=True),
        sa.Column('git_credential_type', sa.String(20), nullable=True),
        sa.Column('git_ssh_key_path', sa.String(500), nullable=True),
        sa.Column('git_https_username', sa.String(200), nullable=True),
        sa.Column('git_https_token', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('global_settings')
