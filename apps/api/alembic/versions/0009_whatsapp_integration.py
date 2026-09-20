"""create whatsapp_integration tables

Revision ID: 0009_whatsapp_integration
Revises: 0008_browser_runs
Create Date: 2026-09-20 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0009_whatsapp_integration'
down_revision = '0008_browser_runs'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. authorized_developers table
    op.create_table(
        'authorized_developers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('phone_number', sa.String(length=50), nullable=False),
        sa.Column('identity_hash', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='DEVELOPER'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_authorized_developers_phone_number', 'authorized_developers', ['phone_number'], unique=True)
    op.create_index('ix_authorized_developers_identity_hash', 'authorized_developers', ['identity_hash'], unique=True)

    # 2. whatsapp_conversations table
    op.create_table(
        'whatsapp_conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('developer_id', sa.String(length=36), nullable=False),
        sa.Column('phone_number', sa.String(length=50), nullable=False),
        sa.Column('active_project_id', sa.String(length=36), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='IDLE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['developer_id'], ['authorized_developers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['active_project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. whatsapp_messages table
    op.create_table(
        'whatsapp_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=True),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('sender_phone', sa.String(length=50), nullable=False),
        sa.Column('recipient_phone', sa.String(length=50), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('parsed_command', sa.JSON(), nullable=True),
        sa.Column('command_type', sa.String(length=50), nullable=True),
        sa.Column('is_authorized', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_redacted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='SENT'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['whatsapp_conversations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_whatsapp_messages_provider_message_id', 'whatsapp_messages', ['provider_message_id'], unique=True)

    # 4. confirmation_tokens table
    op.create_table(
        'confirmation_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('token', sa.String(length=16), nullable=False),
        sa.Column('developer_id', sa.String(length=36), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['developer_id'], ['authorized_developers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_confirmation_tokens_token', 'confirmation_tokens', ['token'], unique=True)

def downgrade() -> None:
    op.drop_index('ix_confirmation_tokens_token', table_name='confirmation_tokens')
    op.drop_table('confirmation_tokens')
    op.drop_index('ix_whatsapp_messages_provider_message_id', table_name='whatsapp_messages')
    op.drop_table('whatsapp_messages')
    op.drop_table('whatsapp_conversations')
    op.drop_index('ix_authorized_developers_identity_hash', table_name='authorized_developers')
    op.drop_index('ix_authorized_developers_phone_number', table_name='authorized_developers')
    op.drop_table('authorized_developers')
