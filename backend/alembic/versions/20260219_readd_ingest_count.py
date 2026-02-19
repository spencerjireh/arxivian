"""Re-add ingest_count to usage_counters for daily ingest quota.

Revision ID: 015_readd_ingest_count
Revises: 014_add_thinking_steps
Create Date: 2026-02-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "015_readd_ingest_count"
down_revision: Union[str, None] = "014_add_thinking_steps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Re-add ingest_count column dropped in 011_add_user_tiers."""
    op.add_column(
        "usage_counters",
        sa.Column("ingest_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("usage_counters", "ingest_count")
