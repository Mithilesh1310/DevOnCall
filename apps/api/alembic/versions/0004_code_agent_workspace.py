"""code agent workspace schema

Revision ID: 0004_code_agent_workspace
Revises: 0003_agent_runtime
Create Date: 2026-09-20 13:54:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0004_code_agent_workspace'
down_revision: Union[str, None] = '0003_agent_runtime'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('agent_runs', sa.Column('workspace_path', sa.String(length=512), nullable=True))
    op.add_column('agent_runs', sa.Column('agent_branch', sa.String(length=255), nullable=True))
    op.add_column('agent_runs', sa.Column('base_commit_sha', sa.String(length=64), nullable=True))
    op.add_column('agent_runs', sa.Column('change_plan', sa.JSON(), nullable=True))
    op.add_column('agent_runs', sa.Column('diff_summary', sa.JSON(), nullable=True))
    op.add_column('agent_runs', sa.Column('pull_request_url', sa.String(length=512), nullable=True))
    op.add_column('agent_runs', sa.Column('pull_request_status', sa.String(length=50), nullable=True))
    op.add_column('agent_runs', sa.Column('approved_by', sa.String(length=255), nullable=True))
    op.add_column('agent_runs', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column('agent_runs', 'approved_at')
    op.drop_column('agent_runs', 'approved_by')
    op.drop_column('agent_runs', 'pull_request_status')
    op.drop_column('agent_runs', 'pull_request_url')
    op.drop_column('agent_runs', 'diff_summary')
    op.drop_column('agent_runs', 'change_plan')
    op.drop_column('agent_runs', 'base_commit_sha')
    op.drop_column('agent_runs', 'agent_branch')
    op.drop_column('agent_runs', 'workspace_path')
