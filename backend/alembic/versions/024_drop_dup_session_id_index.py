"""Drop the redundant unique index on conversations.session_id (ARX-65).

Revision ID: 024_drop_dup_session_id_index
Revises: 023_drop_paper_scores_details
Create Date: 2026-09-30

003_add_conversations created two unique objects on this one column: the inline
`unique=True` inside `create_table`, which PostgreSQL names
`conversations_session_id_key` and backs with an implicit index, and this explicit
unique index. That implicit index already serves every lookup, so the second one only
costs writes. Uniqueness itself is unchanged -- the constraint stays.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "024_drop_dup_session_id_index"
down_revision: str | None = "023_drop_paper_scores_details"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("idx_conversations_session_id", table_name="conversations")


def downgrade() -> None:
    op.create_index("idx_conversations_session_id", "conversations", ["session_id"], unique=True)
