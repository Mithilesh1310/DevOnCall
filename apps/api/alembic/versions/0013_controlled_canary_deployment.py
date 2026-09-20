"""create controlled canary deployment and production safety gate tables

Revision ID: 0013_controlled_canary_deployment
Revises: 0012_production_observability
Create Date: 2026-09-20 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0013_controlled_canary_deployment'
down_revision = '0012_production_observability'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # release_candidates
    op.create_table(
        'release_candidates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('staging_deployment_id', sa.String(length=36), nullable=True),
        sa.Column('pr_url', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='CREATED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rc_project_id', 'release_candidates', ['project_id'])
    op.create_index('ix_rc_commit_sha', 'release_candidates', ['commit_sha'])
    op.create_index('ix_rc_status', 'release_candidates', ['status'])

    # production_approvals
    op.create_table(
        'production_approvals',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rc_id', sa.String(length=36), nullable=False),
        sa.Column('approval_type', sa.String(length=50), nullable=False),
        sa.Column('approver_id', sa.String(length=255), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('confirmation_token', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['rc_id'], ['release_candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prod_appr_rc_id', 'production_approvals', ['rc_id'])
    op.create_index('ix_prod_appr_token', 'production_approvals', ['confirmation_token'])

    # canary_deployments
    op.create_table(
        'canary_deployments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rc_id', sa.String(length=36), nullable=False),
        sa.Column('traffic_percent', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='STARTING'),
        sa.Column('deployment_url', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['rc_id'], ['release_candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_canary_dep_rc_id', 'canary_deployments', ['rc_id'])
    op.create_index('ix_canary_dep_status', 'canary_deployments', ['status'])

    # canary_verification_records
    op.create_table(
        'canary_verification_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('canary_id', sa.String(length=36), nullable=False),
        sa.Column('verdict', sa.String(length=50), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('insufficient_data_reasons', sa.JSON(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['canary_id'], ['canary_deployments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_canary_ver_canary_id', 'canary_verification_records', ['canary_id'])

    # production_deployments
    op.create_table(
        'production_deployments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rc_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DEPLOYING'),
        sa.Column('deployment_url', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['rc_id'], ['release_candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prod_dep_rc_id', 'production_deployments', ['rc_id'])
    op.create_index('ix_prod_dep_status', 'production_deployments', ['status'])

    # rollback_records
    op.create_table(
        'rollback_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('deployment_id', sa.String(length=36), nullable=True),
        sa.Column('rc_id', sa.String(length=36), nullable=False),
        sa.Column('target_commit_sha', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('initiated_by', sa.String(length=255), nullable=False),
        sa.Column('initiated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['deployment_id'], ['production_deployments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rollback_rc_id', 'rollback_records', ['rc_id'])
    op.create_index('ix_rollback_status', 'rollback_records', ['status'])

    # deployment_audit_logs
    op.create_table(
        'deployment_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rc_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('actor', sa.String(length=255), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['rc_id'], ['release_candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_dep_audit_rc_id', 'deployment_audit_logs', ['rc_id'])
    op.create_index('ix_dep_audit_event_type', 'deployment_audit_logs', ['event_type'])


def downgrade() -> None:
    op.drop_table('deployment_audit_logs')
    op.drop_table('rollback_records')
    op.drop_table('production_deployments')
    op.drop_table('canary_verification_records')
    op.drop_table('canary_deployments')
    op.drop_table('production_approvals')
    op.drop_table('release_candidates')
