"""merge heads

Revision ID: 71f72226a5f5
Revises: add_engineer_chat_fields, da91de8b6e4a
Create Date: 2025-07-03 17:31:28.932396

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '71f72226a5f5'
down_revision = ('add_engineer_chat_fields', 'da91de8b6e4a')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
