"""Scope reports to users - add user_id FK, delete global reports.

Revision ID: 010_scope_reports_to_users
Revises: 009_add_usage_counters
Create Date: 2026-02-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "010_scope_reports_to_users"
down_revision: Union[str, None] = "009_add_usage_counters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id to reports table and scope to users."""
    # Add user_id column as nullable first
    op.add_column(
        "reports",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key("fk_reports_user_id", "reports", "users", ["user_id"], ["id"])

    # Delete existing global reports (meaningless under new schema)
    op.execute("DELETE FROM reports")

    # Make user_id NOT NULL
    op.alter_column("reports", "user_id", nullable=False)

    # Add indexes
    op.create_index("ix_reports_user_id", "reports", ["user_id"])
    op.create_index("ix_reports_user_id_created_at", "reports", ["user_id", "created_at"])

    # Unique constraint to prevent duplicate daily reports per user
    op.create_unique_constraint(
        "uq_reports_user_type_start", "reports", ["user_id", "report_type", "period_start"]
    )


def downgrade() -> None:
    """Remove user_id from reports table."""
    op.drop_constraint("uq_reports_user_type_start", "reports", type_="unique")
    op.drop_index("ix_reports_user_id_created_at", table_name="reports")
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_constraint("fk_reports_user_id", "reports", type_="foreignkey")
    op.drop_column("reports", "user_id")
