"""Add agent_executions table for state persistence.

Revision ID: 004_add_agent_executions
Revises: 003_add_conversations
Create Date: 2024-12-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_add_agent_executions"
down_revision: Union[str, None] = "003_add_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent_executions table for state persistence."""

    # Create execution status enum
    op.execute(
        """
        CREATE TYPE execution_status AS ENUM (
            'running',
            'paused',
            'completed',
            'failed'
        )
        """
    )

    # Create agent_executions table
    op.create_table(
        "agent_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "running", "paused", "completed", "failed",
                name="execution_status",
                create_type=False,
            ),
            nullable=False,
            default="running",
        ),
        sa.Column("state_snapshot", postgresql.JSONB, nullable=False),
        sa.Column("iteration", sa.Integer, nullable=False, default=0),
        sa.Column("pause_reason", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
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

    # Create indexes
    op.create_index(
        "idx_agent_executions_session_id",
        "agent_executions",
        ["session_id"],
    )

    op.create_index(
        "idx_agent_executions_status",
        "agent_executions",
        ["status"],
    )

    # Create index for finding paused executions
    op.create_index(
        "idx_agent_executions_status_session",
        "agent_executions",
        ["session_id", "status"],
    )


def downgrade() -> None:
    """Drop agent_executions table."""

    op.drop_index("idx_agent_executions_status_session", table_name="agent_executions")
    op.drop_index("idx_agent_executions_status", table_name="agent_executions")
    op.drop_index("idx_agent_executions_session_id", table_name="agent_executions")
    op.drop_table("agent_executions")

    op.execute("DROP TYPE execution_status")
