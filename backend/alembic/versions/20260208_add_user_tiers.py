"""Add user tiers, paper ownership, drop ingest_count, seed system user.

Revision ID: 011_add_user_tiers
Revises: 010_scope_reports_to_users
Create Date: 2026-02-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "011_add_user_tiers"
down_revision: Union[str, None] = "010_scope_reports_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add tier column to users
    op.add_column(
        "users",
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
    )

    # 2. Drop ingest_count from usage_counters
    op.drop_column("usage_counters", "ingest_count")

    # 3. Seed system user
    op.execute(
        "INSERT INTO users (id, clerk_id, email, first_name, tier) "
        "VALUES (gen_random_uuid(), 'system', 'system@arxivian.local', 'Arxivian', 'pro') "
        "ON CONFLICT (clerk_id) DO NOTHING"
    )

    # 4. Add user_id to papers (nullable first for backfill)
    op.add_column(
        "papers",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key("fk_papers_user_id", "papers", "users", ["user_id"], ["id"])

    # 5. Backfill existing papers to system user
    op.execute(
        "UPDATE papers SET user_id = (SELECT id FROM users WHERE clerk_id = 'system')"
    )

    # 6. Make user_id NOT NULL
    op.alter_column("papers", "user_id", nullable=False)

    # 7. Add index on user_id
    op.create_index("ix_papers_user_id", "papers", ["user_id"])

    # 8. Replace global arxiv_id unique with per-user unique
    op.drop_constraint("papers_arxiv_id_key", "papers", type_="unique")
    op.create_unique_constraint("uq_papers_user_arxiv", "papers", ["user_id", "arxiv_id"])


def downgrade() -> None:
    # Reverse per-user unique constraint
    op.drop_constraint("uq_papers_user_arxiv", "papers", type_="unique")
    op.create_unique_constraint("papers_arxiv_id_key", "papers", ["arxiv_id"])

    # Remove user_id from papers
    op.drop_index("ix_papers_user_id", table_name="papers")
    op.drop_constraint("fk_papers_user_id", "papers", type_="foreignkey")
    op.drop_column("papers", "user_id")

    # Re-add ingest_count
    op.add_column(
        "usage_counters",
        sa.Column("ingest_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Remove system user (best-effort)
    op.execute("DELETE FROM users WHERE clerk_id = 'system'")

    # Remove tier column
    op.drop_column("users", "tier")
