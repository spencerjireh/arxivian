"""Add task_executions and reports tables, add indexes for cleanup performance.

Revision ID: 008_celery_improvements
Revises: 007_add_user_preferences
Create Date: 2025-02-07

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008_celery_improvements"
down_revision: Union[str, None] = "007_add_user_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create task_executions and reports tables, add performance indexes."""
    # Create task_executions table
    op.create_table(
        "task_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("celery_task_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
    )

    # Create reports table
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_type", sa.String(100), nullable=False),
        sa.Column("period_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("period_end", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
    )

    # Add indexes for cleanup task performance
    op.create_index(
        "ix_conversations_created_at", "conversations", ["created_at"]
    )
    op.create_index(
        "ix_agent_executions_created_at", "agent_executions", ["created_at"]
    )


def downgrade() -> None:
    """Drop indexes and tables."""
    op.drop_index("ix_agent_executions_created_at", table_name="agent_executions")
    op.drop_index("ix_conversations_created_at", table_name="conversations")
    op.drop_table("reports")
    op.drop_table("task_executions")
