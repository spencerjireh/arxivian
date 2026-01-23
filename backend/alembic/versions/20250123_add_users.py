"""Add users table for Clerk authentication.

Revision ID: 005_add_users
Revises: 004_add_agent_executions
Create Date: 2025-01-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_add_users"
down_revision: Union[str, None] = "004_add_agent_executions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table."""

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clerk_id", sa.String(255), unique=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("profile_image_url", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Create index on clerk_id for fast lookups
    op.create_index("idx_users_clerk_id", "users", ["clerk_id"], unique=True)

    # Create index on email for potential email lookups
    op.create_index("idx_users_email", "users", ["email"], unique=False)


def downgrade() -> None:
    """Drop users table."""

    op.drop_index("idx_users_email", table_name="users")
    op.drop_index("idx_users_clerk_id", table_name="users")
    op.drop_table("users")
