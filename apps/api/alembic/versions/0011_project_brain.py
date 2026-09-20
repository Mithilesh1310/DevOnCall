"""create project_brain_nodes, project_brain_edges, and project_brain_events tables

Revision ID: 0011_project_brain
Revises: 0010_staging_deployments
Create Date: 2026-09-20 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0011_project_brain'
down_revision = '0010_staging_deployments'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. project_brain_nodes
    op.create_table(
        'project_brain_nodes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False, server_default='REPOSITORY_SCAN'),
        sa.Column('source_reference', sa.String(length=255), nullable=False),
        sa.Column('confidence', sa.String(length=50), nullable=False, server_default='VERIFIED'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('metadata_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_brain_nodes_project_id', 'project_brain_nodes', ['project_id'], unique=False)
    op.create_index('ix_project_brain_nodes_node_type', 'project_brain_nodes', ['node_type'], unique=False)
    op.create_index('ix_project_brain_nodes_key', 'project_brain_nodes', ['key'], unique=False)

    # 2. project_brain_edges
    op.create_table(
        'project_brain_edges',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('source_node_id', sa.String(length=36), nullable=False),
        sa.Column('target_node_id', sa.String(length=36), nullable=False),
        sa.Column('relation', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.String(length=50), nullable=False, server_default='VERIFIED'),
        sa.Column('source_reference', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_node_id'], ['project_brain_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['project_brain_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_brain_edges_project_id', 'project_brain_edges', ['project_id'], unique=False)
    op.create_index('ix_project_brain_edges_source_node_id', 'project_brain_edges', ['source_node_id'], unique=False)
    op.create_index('ix_project_brain_edges_target_node_id', 'project_brain_edges', ['target_node_id'], unique=False)

    # 3. project_brain_events
    op.create_table(
        'project_brain_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_brain_events_project_id', 'project_brain_events', ['project_id'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_project_brain_events_project_id', table_name='project_brain_events')
    op.drop_table('project_brain_events')
    op.drop_index('ix_project_brain_edges_target_node_id', table_name='project_brain_edges')
    op.drop_index('ix_project_brain_edges_source_node_id', table_name='project_brain_edges')
    op.drop_index('ix_project_brain_edges_project_id', table_name='project_brain_edges')
    op.drop_table('project_brain_edges')
    op.drop_index('ix_project_brain_nodes_key', table_name='project_brain_nodes')
    op.drop_index('ix_project_brain_nodes_node_type', table_name='project_brain_nodes')
    op.drop_index('ix_project_brain_nodes_project_id', table_name='project_brain_nodes')
    op.drop_table('project_brain_nodes')
