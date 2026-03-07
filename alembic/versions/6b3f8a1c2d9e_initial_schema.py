"""Initial schema

Revision ID: 6b3f8a1c2d9e
Revises:
Create Date: 2025-01-01 00:00:00.000000

Captures the full database schema as it existed before the loop-task feature
was introduced. All tables are created here; any subsequent structural changes
live in later revisions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '6b3f8a1c2d9e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'instances',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('pid', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('current_task_id', sa.Integer(), nullable=True),
        sa.Column('worktree_path', sa.String(length=500), nullable=True),
        sa.Column('worktree_branch', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=50), nullable=True),
        sa.Column('total_tasks_completed', sa.Integer(), nullable=True),
        sa.Column('total_cost_usd', sa.Float(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('git_url', sa.String(length=500), nullable=True),
        sa.Column('has_remote', sa.Boolean(), nullable=True),
        sa.Column('local_path', sa.String(length=500), nullable=True),
        sa.Column('default_branch', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('target_repo', sa.String(length=500), nullable=True),
        sa.Column('target_branch', sa.String(length=100), nullable=True),
        sa.Column('result_branch', sa.String(length=100), nullable=True),
        sa.Column('merge_status', sa.String(length=20), nullable=True),
        sa.Column('instance_id', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('mode', sa.String(length=20), nullable=True),
        sa.Column('plan_content', sa.Text(), nullable=True),
        sa.Column('plan_approved', sa.Boolean(), nullable=True),
        sa.Column('session_id', sa.String(length=200), nullable=True),
        sa.Column('last_cwd', sa.String(length=500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tasks_priority', 'tasks', ['priority'])
    op.create_index('ix_tasks_project_id', 'tasks', ['project_id'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])

    op.create_table(
        'log_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('tool_name', sa.String(length=100), nullable=True),
        sa.Column('tool_input', sa.Text(), nullable=True),
        sa.Column('tool_output', sa.Text(), nullable=True),
        sa.Column('raw_json', sa.Text(), nullable=True),
        sa.Column('is_error', sa.Boolean(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_log_entries_event_type', 'log_entries', ['event_type'])
    op.create_index('ix_log_entries_instance_id', 'log_entries', ['instance_id'])
    op.create_index('ix_log_entries_task_id', 'log_entries', ['task_id'])

    op.create_table(
        'worktrees',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('repo_path', sa.String(length=500), nullable=False),
        sa.Column('worktree_path', sa.String(length=500), nullable=False),
        sa.Column('branch_name', sa.String(length=100), nullable=False),
        sa.Column('base_branch', sa.String(length=100), nullable=True),
        sa.Column('instance_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('removed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('worktree_path'),
    )


def downgrade() -> None:
    op.drop_table('worktrees')
    op.drop_index('ix_log_entries_task_id', table_name='log_entries')
    op.drop_index('ix_log_entries_instance_id', table_name='log_entries')
    op.drop_index('ix_log_entries_event_type', table_name='log_entries')
    op.drop_table('log_entries')
    op.drop_index('ix_tasks_status', table_name='tasks')
    op.drop_index('ix_tasks_project_id', table_name='tasks')
    op.drop_index('ix_tasks_priority', table_name='tasks')
    op.drop_table('tasks')
    op.drop_table('projects')
    op.drop_table('instances')
