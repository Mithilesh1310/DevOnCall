"""create browser_runs and browser_step_results tables

Revision ID: 0008_browser_runs
Revises: 0007_validation_attempts
Create Date: 2026-09-20 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0008_browser_runs'
down_revision = '0007_validation_attempts'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'browser_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('agent_run_id', sa.String(length=36), nullable=True),
        sa.Column('workspace_id', sa.String(length=255), nullable=False),
        sa.Column('scenario_id', sa.String(length=100), nullable=False),
        sa.Column('provider_type', sa.String(length=50), nullable=False, server_default='MOCK_BROWSER'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='QUEUED'),
        sa.Column('base_url', sa.String(length=255), nullable=False),
        sa.Column('current_url', sa.String(length=255), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('step_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('suspected_file', sa.String(length=255), nullable=True),
        sa.Column('artifact_paths', sa.JSON(), nullable=True),
        sa.Column('console_errors', sa.JSON(), nullable=True),
        sa.Column('network_errors', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_browser_runs_project_id', 'browser_runs', ['project_id'], unique=False)
    op.create_index('ix_browser_runs_agent_run_id', 'browser_runs', ['agent_run_id'], unique=False)
    op.create_index('ix_browser_runs_workspace_id', 'browser_runs', ['workspace_id'], unique=False)

    op.create_table(
        'browser_step_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('browser_run_id', sa.String(length=36), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('selector', sa.String(length=255), nullable=True),
        sa.Column('selector_strategy', sa.String(length=50), nullable=False, server_default='STABLE_CSS'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PASSED'),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('screenshot_path', sa.String(length=255), nullable=True),
        sa.Column('observed_value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['browser_run_id'], ['browser_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_browser_step_results_browser_run_id', 'browser_step_results', ['browser_run_id'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_browser_step_results_browser_run_id', table_name='browser_step_results')
    op.drop_table('browser_step_results')
    op.drop_index('ix_browser_runs_workspace_id', table_name='browser_runs')
    op.drop_index('ix_browser_runs_agent_run_id', table_name='browser_runs')
    op.drop_index('ix_browser_runs_project_id', table_name='browser_runs')
    op.drop_table('browser_runs')
