"""Drop the task_executions table (ARX-74).

Revision ID: 026_drop_task_executions
Revises: 025_drop_demand_score
Create Date: 2026-10-10

The table was permanently empty in production. The Celery signal handlers only ever issued
UPDATEs and no-op'd silently when no row existed, and nothing inserted rows for scheduled
tasks -- only three HTTP paths did. So `GET /ops/tasks/{id}` 404'd for every task that
actually ran on a schedule, which is the opposite of an audit trail. Task outcomes live in
Loki, which is what surfaced the ARX-67 triage outage.

Downgrade recreates the table empty; its contents were never meaningful.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "026_drop_task_executions"
down_revision: str | None = "025_drop_demand_score"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("task_executions")


def downgrade() -> None:
    # Mirrors 008_celery_improvements exactly, so a round trip is a true inverse.
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
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
