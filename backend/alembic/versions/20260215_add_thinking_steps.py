"""Add thinking_steps column to conversation_turns.

Revision ID: 014_add_thinking_steps
Revises: 013_drop_reports_table
Create Date: 2026-02-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "014_add_thinking_steps"
down_revision: Union[str, None] = "013_drop_reports_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add thinking_steps JSONB column for persisting structured step data."""
    op.add_column("conversation_turns", sa.Column("thinking_steps", JSONB, nullable=True))


def downgrade() -> None:
    """Remove thinking_steps column."""
    op.drop_column("conversation_turns", "thinking_steps")
