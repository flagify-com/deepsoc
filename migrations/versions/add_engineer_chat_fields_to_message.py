"""Add engineer chat fields to message table

Revision ID: add_engineer_chat_fields
Revises: f68b4187b0dc
Create Date: 2025-01-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_engineer_chat_fields'
down_revision = 'f68b4187b0dc'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('message_category', sa.String(length=32), server_default='agent', nullable=True))
        batch_op.add_column(sa.Column('chat_session_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('sender_type', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('event_summary_version', sa.String(length=64), nullable=True))

def downgrade():
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_column('event_summary_version')
        batch_op.drop_column('sender_type')
        batch_op.drop_column('chat_session_id')
        batch_op.drop_column('message_category')