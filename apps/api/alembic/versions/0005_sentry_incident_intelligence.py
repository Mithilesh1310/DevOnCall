"""sentry incident intelligence schema

Revision ID: 0005_sentry_incident_intelligence
Revises: 0004_code_agent_workspace
Create Date: 2026-09-20 14:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0005_sentry_incident_intelligence'
down_revision: Union[str, None] = '0004_code_agent_workspace'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add Sentry fields to incidents table
    op.add_column('incidents', sa.Column('external_event_id', sa.String(length=255), nullable=True))
    op.add_column('incidents', sa.Column('external_issue_id', sa.String(length=255), nullable=True))
    op.add_column('incidents', sa.Column('error_type', sa.String(length=255), nullable=True))
    op.add_column('incidents', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('incidents', sa.Column('environment', sa.String(length=100), nullable=True))
    op.add_column('incidents', sa.Column('release', sa.String(length=100), nullable=True))
    op.add_column('incidents', sa.Column('commit_sha', sa.String(length=64), nullable=True))
    op.add_column('incidents', sa.Column('culprit', sa.String(length=255), nullable=True))
    op.add_column('incidents', sa.Column('occurrence_count', sa.Integer(), server_default='1', nullable=False))
    op.add_column('incidents', sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('incidents', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('incidents', sa.Column('stack_trace', sa.JSON(), nullable=True))
    op.add_column('incidents', sa.Column('normalized_metadata', sa.JSON(), nullable=True))

    # Create incident_investigations table
    op.create_table(
        'incident_investigations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('incident_id', sa.String(length=36), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('hypothesis', sa.JSON(), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('relevant_files', sa.JSON(), nullable=True),
        sa.Column('relevant_stack_frames', sa.JSON(), nullable=True),
        sa.Column('repository_matches', sa.JSON(), nullable=True),
        sa.Column('suspected_locations', sa.JSON(), nullable=True),
        sa.Column('proposed_fix', sa.JSON(), nullable=True),
        sa.Column('recommended_next_action', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )

def downgrade() -> None:
    op.drop_table('incident_investigations')
    op.drop_column('incidents', 'normalized_metadata')
    op.drop_column('incidents', 'stack_trace')
    op.drop_column('incidents', 'last_seen_at')
    op.drop_column('incidents', 'first_seen_at')
    op.drop_column('incidents', 'occurrence_count')
    op.drop_column('incidents', 'culprit')
    op.drop_column('incidents', 'commit_sha')
    op.drop_column('incidents', 'release')
    op.drop_column('incidents', 'environment')
    op.drop_column('incidents', 'error_message')
    op.drop_column('incidents', 'error_type')
    op.drop_column('incidents', 'external_issue_id')
    op.drop_column('incidents', 'external_event_id')
