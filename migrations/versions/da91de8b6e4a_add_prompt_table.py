"""Add Prompt table

Revision ID: da91de8b6e4a
Revises: 4b689ba9b54b
Create Date: 2025-03-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'da91de8b6e4a'
down_revision = '4b689ba9b54b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'prompts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=64), nullable=False, unique=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('prompts')
