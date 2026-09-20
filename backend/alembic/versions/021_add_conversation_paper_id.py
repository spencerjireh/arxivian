"""Add conversations.paper_id for paper-scoped chat (SPE-277).

Revision ID: 021_add_conversation_paper_id
Revises: 020_add_score_dimensions
Create Date: 2026-09-20

A conversation started from a paper detail page is scoped to that paper for its whole
life: retrieval stays inside the paper and the corpus-level tools are hidden. The scope
is persisted here so follow-up turns and resumes stay narrowed without the client
re-sending it. ON DELETE SET NULL: deleting a paper un-scopes its threads instead of
deleting them.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "021_add_conversation_paper_id"
down_revision: str | None = "020_add_score_dimensions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "paper_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("papers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_conversations_paper_id", "conversations", ["paper_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_paper_id", table_name="conversations")
    op.drop_column("conversations", "paper_id")
