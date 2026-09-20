"""isolated docker sandbox schema

Revision ID: 0006_sandbox_runs
Revises: 0005_sentry_incident_intelligence
Create Date: 2026-09-20 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0006_sandbox_runs'
down_revision: Union[str, None] = '0005_sentry_incident_intelligence'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'sandbox_runs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('agent_run_id', sa.String(length=36), nullable=True),
        sa.Column('workspace_id', sa.String(length=255), nullable=False),
        sa.Column('command_type', sa.String(length=50), nullable=False),
        sa.Column('runtime', sa.String(length=50), server_default='python', nullable=False),
        sa.Column('provider_type', sa.String(length=50), server_default='MOCK_SANDBOX', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='QUEUED', nullable=False),
        sa.Column('exit_code', sa.Integer(), server_default='-1', nullable=False),
        sa.Column('stdout', sa.Text(), server_default='', nullable=False),
        sa.Column('stderr', sa.Text(), server_default='', nullable=False),
        sa.Column('duration_ms', sa.Integer(), server_default='0', nullable=False),
        sa.Column('timeout_seconds', sa.Integer(), server_default='120', nullable=False),
        sa.Column('resource_limits', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    op.create_index('ix_sandbox_runs_project_id', 'sandbox_runs', ['project_id'])
    op.create_index('ix_sandbox_runs_agent_run_id', 'sandbox_runs', ['agent_run_id'])
    op.create_index('ix_sandbox_runs_workspace_id', 'sandbox_runs', ['workspace_id'])

def downgrade() -> None:
    op.drop_index('ix_sandbox_runs_workspace_id', table_name='sandbox_runs')
    op.drop_index('ix_sandbox_runs_agent_run_id', table_name='sandbox_runs')
    op.drop_index('ix_sandbox_runs_project_id', table_name='sandbox_runs')
    op.drop_table('sandbox_runs')
