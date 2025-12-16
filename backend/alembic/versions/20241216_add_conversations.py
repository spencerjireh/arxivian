"""Add conversations and conversation_turns tables.

Revision ID: 003_add_conversations
Revises: 002_add_timezone
Create Date: 2024-12-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_add_conversations"
down_revision: Union[str, None] = "002_add_timezone"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create conversations and conversation_turns tables."""

    # Create conversations table
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(255), unique=True, nullable=False),
        sa.Column("metadata_", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create index on session_id
    op.create_index(
        "idx_conversations_session_id", "conversations", ["session_id"], unique=True
    )

    # Create conversation_turns table
    op.create_table(
        "conversation_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_number", sa.Integer, nullable=False),
        sa.Column("user_query", sa.Text, nullable=False),
        sa.Column("agent_response", sa.Text, nullable=False),
        sa.Column("guardrail_score", sa.Integer, nullable=True),
        sa.Column("retrieval_attempts", sa.Integer, default=1),
        sa.Column("rewritten_query", sa.Text, nullable=True),
        sa.Column("sources", postgresql.JSONB, nullable=True),
        sa.Column("reasoning_steps", postgresql.JSONB, nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create index on conversation_id
    op.create_index(
        "idx_conversation_turns_conversation_id",
        "conversation_turns",
        ["conversation_id"],
    )

    # Create unique constraint on (conversation_id, turn_number)
    op.create_unique_constraint(
        "uq_conversation_turns_conversation_id_turn_number",
        "conversation_turns",
        ["conversation_id", "turn_number"],
    )


def downgrade() -> None:
    """Drop conversations and conversation_turns tables."""

    op.drop_constraint(
        "uq_conversation_turns_conversation_id_turn_number",
        "conversation_turns",
        type_="unique",
    )
    op.drop_index("idx_conversation_turns_conversation_id", table_name="conversation_turns")
    op.drop_table("conversation_turns")

    op.drop_index("idx_conversations_session_id", table_name="conversations")
    op.drop_table("conversations")
