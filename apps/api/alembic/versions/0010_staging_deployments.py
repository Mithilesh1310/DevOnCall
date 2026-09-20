"""create staging_deployments and staging_check_results tables

Revision ID: 0010_staging_deployments
Revises: 0009_whatsapp_integration
Create Date: 2026-09-20 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0010_staging_deployments'
down_revision = '0009_whatsapp_integration'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'staging_deployments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('agent_run_id', sa.String(length=36), nullable=True),
        sa.Column('workspace_id', sa.String(length=255), nullable=False),
        sa.Column('branch', sa.String(length=255), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('environment', sa.String(length=50), nullable=False, server_default='STAGING'),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='MOCK_STAGING'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='QUEUED'),
        sa.Column('deployment_url', sa.String(length=255), nullable=True),
        sa.Column('health_status', sa.String(length=50), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_staging_deployments_project_id', 'staging_deployments', ['project_id'], unique=False)
    op.create_index('ix_staging_deployments_agent_run_id', 'staging_deployments', ['agent_run_id'], unique=False)
    op.create_index('ix_staging_deployments_commit_sha', 'staging_deployments', ['commit_sha'], unique=False)

    op.create_table(
        'staging_check_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('deployment_id', sa.String(length=36), nullable=False),
        sa.Column('check_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PASS'),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['deployment_id'], ['staging_deployments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_staging_check_results_deployment_id', 'staging_check_results', ['deployment_id'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_staging_check_results_deployment_id', table_name='staging_check_results')
    op.drop_table('staging_check_results')
    op.drop_index('ix_staging_deployments_commit_sha', table_name='staging_deployments')
    op.drop_index('ix_staging_deployments_agent_run_id', table_name='staging_deployments')
    op.drop_index('ix_staging_deployments_project_id', table_name='staging_deployments')
    op.drop_table('staging_deployments')
