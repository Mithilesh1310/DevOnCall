"""agent runtime schema

Revision ID: 0003_agent_runtime
Revises: 0002_github_integration
Create Date: 2026-09-20 13:36:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_agent_runtime'
down_revision: Union[str, None] = '0002_github_integration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Make incident_id nullable for project-level agent runs
    op.alter_column('agent_runs', 'incident_id', existing_type=sa.String(length=36), nullable=True)
    
    # Add new agent runtime fields
    op.add_column('agent_runs', sa.Column('project_id', sa.String(length=36), nullable=True))
    op.add_column('agent_runs', sa.Column('user_task', sa.Text(), nullable=True))
    op.add_column('agent_runs', sa.Column('current_goal', sa.String(length=512), nullable=True))
    op.add_column('agent_runs', sa.Column('current_step', sa.Integer(), server_default='0', nullable=False))
    op.add_column('agent_runs', sa.Column('iteration_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('agent_runs', sa.Column('execution_metadata', sa.JSON(), nullable=True))
    op.add_column('agent_runs', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agent_runs', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add foreign key constraint to projects table
    op.create_foreign_key('fk_agent_runs_project_id', 'agent_runs', 'projects', ['project_id'], ['id'], ondelete='CASCADE')

def downgrade() -> None:
    op.drop_constraint('fk_agent_runs_project_id', 'agent_runs', type_='foreignkey')
    op.drop_column('agent_runs', 'completed_at')
    op.drop_column('agent_runs', 'started_at')
    op.drop_column('agent_runs', 'execution_metadata')
    op.drop_column('agent_runs', 'iteration_count')
    op.drop_column('agent_runs', 'current_step')
    op.drop_column('agent_runs', 'current_goal')
    op.drop_column('agent_runs', 'user_task')
    op.drop_column('agent_runs', 'project_id')
    op.alter_column('agent_runs', 'incident_id', existing_type=sa.String(length=36), nullable=False)
