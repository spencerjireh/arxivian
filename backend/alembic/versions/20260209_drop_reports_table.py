"""Drop reports table.

Revision ID: 013_drop_reports_table
Revises: 012_communal_knowledge_base
Create Date: 2026-02-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "013_drop_reports_table"
down_revision: Union[str, None] = "012_communal_knowledge_base"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the reports table and all its indexes/constraints."""
    op.drop_index("ix_reports_user_id_created_at", table_name="reports")
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_constraint("uq_reports_user_type_start", "reports", type_="unique")
    op.drop_constraint("fk_reports_user_id", "reports", type_="foreignkey")
    op.drop_table("reports")


def downgrade() -> None:
    """Recreate the reports table."""
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(100), nullable=False),
        sa.Column("period_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("period_end", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("data", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_foreign_key("fk_reports_user_id", "reports", "users", ["user_id"], ["id"])
    op.create_unique_constraint(
        "uq_reports_user_type_start", "reports", ["user_id", "report_type", "period_start"]
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])
    op.create_index("ix_reports_user_id_created_at", "reports", ["user_id", "created_at"])
