"""Add usage_counters table for daily rate limiting.

Revision ID: 009_add_usage_counters
Revises: 008_celery_improvements
Create Date: 2026-02-07

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "009_add_usage_counters"
down_revision: Union[str, None] = "008_celery_improvements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create usage_counters table."""
    op.create_table(
        "usage_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "usage_date",
            sa.Date,
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
        sa.Column("query_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ingest_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_usage_counters_user_date"),
    )
    op.create_index("ix_usage_counters_user_id", "usage_counters", ["user_id"])


def downgrade() -> None:
    """Drop usage_counters table."""
    op.drop_index("ix_usage_counters_user_id", table_name="usage_counters")
    op.drop_table("usage_counters")
