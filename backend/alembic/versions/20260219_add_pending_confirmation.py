"""Add pending_confirmation to conversation_turns for HITL ingest flow.

Revision ID: 016_add_pending_confirmation
Revises: 015_readd_ingest_count
Create Date: 2026-02-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "016_add_pending_confirmation"
down_revision: Union[str, None] = "015_readd_ingest_count"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation_turns",
        sa.Column("pending_confirmation", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation_turns", "pending_confirmation")
