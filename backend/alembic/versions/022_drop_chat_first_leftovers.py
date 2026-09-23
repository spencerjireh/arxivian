"""Drop chat-first leftovers: agent_executions, HITL and ingest-quota columns (ARX-31).

Revision ID: 022_drop_chat_first_leftovers
Revises: 021_add_conversation_paper_id
Create Date: 2026-09-21

Phase 3 narrows chat to the paper-scoped agent with no human-in-the-loop ingestion:

- `agent_executions` was written by the pre-Redis checkpointer and has been empty since
  LangGraph checkpoints moved to Redis; the checkpointer itself is gone now.
- `conversation_turns.pending_confirmation` held the paused HITL proposal.
- `conversation_turns.thinking_steps` fed the thinking-timeline UI, which is removed.
- `usage_counters.ingest_count` counted chat-driven ingests; the ingest tools are gone
  and the tier policy is chats-per-day only.

Downgrade recreates the empty structures so older code can boot.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "022_drop_chat_first_leftovers"
down_revision: str | None = "021_add_conversation_paper_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_agent_executions_created_at", table_name="agent_executions")
    op.drop_index("idx_agent_executions_status_session", table_name="agent_executions")
    op.drop_index("idx_agent_executions_status", table_name="agent_executions")
    op.drop_index("idx_agent_executions_session_id", table_name="agent_executions")
    op.drop_table("agent_executions")
    op.execute("DROP TYPE IF EXISTS execution_status")

    op.drop_column("conversation_turns", "pending_confirmation")
    op.drop_column("conversation_turns", "thinking_steps")
    op.drop_column("usage_counters", "ingest_count")


def downgrade() -> None:
    op.add_column(
        "usage_counters",
        sa.Column("ingest_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "conversation_turns", sa.Column("thinking_steps", postgresql.JSONB, nullable=True)
    )
    op.add_column(
        "conversation_turns", sa.Column("pending_confirmation", postgresql.JSONB, nullable=True)
    )

    op.execute("CREATE TYPE execution_status AS ENUM ('running', 'paused', 'completed', 'failed')")
    op.create_table(
        "agent_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "running",
                "paused",
                "completed",
                "failed",
                name="execution_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("state_snapshot", postgresql.JSONB, nullable=False),
        sa.Column("iteration", sa.Integer, nullable=False),
        sa.Column("pause_reason", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("idx_agent_executions_session_id", "agent_executions", ["session_id"])
    op.create_index("idx_agent_executions_status", "agent_executions", ["status"])
    op.create_index(
        "idx_agent_executions_status_session", "agent_executions", ["session_id", "status"]
    )
    op.create_index("ix_agent_executions_created_at", "agent_executions", ["created_at"])
