"""Add global_settings table

Revision ID: eb3b587c55f1
Revises: e2fb2f8641e9
Create Date: 2025-03-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'eb3b587c55f1'
down_revision = 'e2fb2f8641e9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'global_settings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key', sa.String(length=64), nullable=False, unique=True),
        sa.Column('value', sa.String(length=256), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('global_settings')

