"""automated verification schema

Revision ID: 0007_validation_attempts
Revises: 0006_sandbox_runs
Create Date: 2026-09-20 14:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0007_validation_attempts'
down_revision: Union[str, None] = '0006_sandbox_runs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'validation_attempts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('agent_run_id', sa.String(length=36), nullable=False),
        sa.Column('sandbox_run_id', sa.String(length=36), nullable=True),
        sa.Column('iteration', sa.Integer(), server_default='1', nullable=False),
        sa.Column('command_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('failure_type', sa.String(length=50), nullable=True),
        sa.Column('summary', sa.Text(), server_default='', nullable=False),
        sa.Column('diagnostic_data', sa.JSON(), nullable=True),
        sa.Column('action_taken', sa.String(length=50), server_default='CONTINUE', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    op.create_index('ix_validation_attempts_agent_run_id', 'validation_attempts', ['agent_run_id'])
    op.create_index('ix_validation_attempts_sandbox_run_id', 'validation_attempts', ['sandbox_run_id'])

def downgrade() -> None:
    op.drop_index('ix_validation_attempts_sandbox_run_id', table_name='validation_attempts')
    op.drop_index('ix_validation_attempts_agent_run_id', table_name='validation_attempts')
    op.drop_table('validation_attempts')
