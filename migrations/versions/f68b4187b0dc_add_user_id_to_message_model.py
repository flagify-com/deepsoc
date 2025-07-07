"""Add user_id field to messages

Revision ID: f68b4187b0dc
Revises: eb3b587c55f1
Create Date: 2025-05-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f68b4187b0dc'
down_revision = 'eb3b587c55f1'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=64), nullable=True))

    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_column('user_id')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('user_id')

