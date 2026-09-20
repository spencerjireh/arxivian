"""Add title column to conversations.

Revision ID: 018_add_conversation_title
Revises: 017_add_citations
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "018_add_conversation_title"
down_revision: str | None = "017_add_citations"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("title", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "title")
