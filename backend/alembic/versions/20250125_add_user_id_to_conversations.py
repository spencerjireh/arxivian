"""Add user_id foreign key to conversations table.

Revision ID: 006_add_user_id_to_conversations
Revises: 005_add_users
Create Date: 2025-01-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006_add_user_id_to_conversations"
down_revision: Union[str, None] = "005_add_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id column to conversations table."""

    # Add user_id column (nullable to support existing conversations)
    op.add_column(
        "conversations",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_conversations_user_id",
        "conversations",
        "users",
        ["user_id"],
        ["id"],
    )

    # Create index for efficient user-based queries
    op.create_index(
        "idx_conversations_user_id",
        "conversations",
        ["user_id"],
    )


def downgrade() -> None:
    """Remove user_id column from conversations table."""

    op.drop_index("idx_conversations_user_id", table_name="conversations")
    op.drop_constraint("fk_conversations_user_id", "conversations", type_="foreignkey")
    op.drop_column("conversations", "user_id")
