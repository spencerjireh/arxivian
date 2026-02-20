"""Add citations JSONB column to conversation_turns.

Revision ID: 017_add_citations
Revises: 016_add_pending_confirmation
Create Date: 2026-02-19
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "017_add_citations"
down_revision: Union[str, None] = "016_add_pending_confirmation"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("conversation_turns", sa.Column("citations", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("conversation_turns", "citations")
