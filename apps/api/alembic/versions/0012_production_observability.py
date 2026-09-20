"""create production_observations table

Revision ID: 0012_production_observability
Revises: 0011_project_brain
Create Date: 2026-09-20 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0012_production_observability'
down_revision = '0011_project_brain'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'production_observations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='generic'),
        sa.Column('external_event_id', sa.String(length=255), nullable=False),
        sa.Column('fingerprint', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False, server_default='error'),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='ERROR'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='OPEN'),
        sa.Column('environment', sa.String(length=50), nullable=False, server_default='PRODUCTION'),
        sa.Column('service', sa.String(length=100), nullable=False, server_default='unknown-service'),
        sa.Column('release', sa.String(length=100), nullable=True),
        sa.Column('commit_sha', sa.String(length=64), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('request_method', sa.String(length=10), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('metadata_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_prod_obs_project_id', 'production_observations', ['project_id'])
    op.create_index('ix_prod_obs_provider', 'production_observations', ['provider'])
    op.create_index('ix_prod_obs_fingerprint', 'production_observations', ['fingerprint'])
    op.create_index('ix_prod_obs_severity', 'production_observations', ['severity'])
    op.create_index('ix_prod_obs_status', 'production_observations', ['status'])
    op.create_index('ix_prod_obs_service', 'production_observations', ['service'])
    op.create_index('ix_prod_obs_commit_sha', 'production_observations', ['commit_sha'])
    op.create_index('ix_prod_obs_first_seen_at', 'production_observations', ['first_seen_at'])
    op.create_index('ix_prod_obs_last_seen_at', 'production_observations', ['last_seen_at'])


def downgrade() -> None:
    op.drop_index('ix_prod_obs_last_seen_at', table_name='production_observations')
    op.drop_index('ix_prod_obs_first_seen_at', table_name='production_observations')
    op.drop_index('ix_prod_obs_commit_sha', table_name='production_observations')
    op.drop_index('ix_prod_obs_service', table_name='production_observations')
    op.drop_index('ix_prod_obs_status', table_name='production_observations')
    op.drop_index('ix_prod_obs_severity', table_name='production_observations')
    op.drop_index('ix_prod_obs_fingerprint', table_name='production_observations')
    op.drop_index('ix_prod_obs_provider', table_name='production_observations')
    op.drop_index('ix_prod_obs_project_id', table_name='production_observations')
    op.drop_table('production_observations')
