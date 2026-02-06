"""Add preferences column to users table.

Revision ID: 007_add_user_preferences
Revises: 006_add_user_id_to_conversations
Create Date: 2025-02-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_add_user_preferences"
down_revision: Union[str, None] = "006_add_user_id_to_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add preferences JSONB column to users table."""
    op.add_column(
        "users",
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    """Remove preferences column from users table."""
    op.drop_column("users", "preferences")
