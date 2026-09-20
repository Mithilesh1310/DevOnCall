"""github integration schema

Revision ID: 0002_github_integration
Revises: 0001_initial
Create Date: 2026-09-20 13:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_github_integration'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('projects', sa.Column('github_owner', sa.String(length=255), nullable=True))
    op.add_column('projects', sa.Column('github_repo', sa.String(length=255), nullable=True))
    op.add_column('projects', sa.Column('github_url', sa.String(length=512), nullable=True))
    op.add_column('projects', sa.Column('last_indexed_commit_sha', sa.String(length=100), nullable=True))
    op.add_column('projects', sa.Column('last_indexed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('projects', sa.Column('repository_snapshot', sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column('projects', 'repository_snapshot')
    op.drop_column('projects', 'last_indexed_at')
    op.drop_column('projects', 'last_indexed_commit_sha')
    op.drop_column('projects', 'github_url')
    op.drop_column('projects', 'github_repo')
    op.drop_column('projects', 'github_owner')
