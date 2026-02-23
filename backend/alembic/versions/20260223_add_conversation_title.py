"""Add title column to conversations.

Revision ID: 018_add_conversation_title
Revises: 017_add_citations
Create Date: 2026-02-23
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "018_add_conversation_title"
down_revision: Union[str, None] = "017_add_citations"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("title", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "title")
