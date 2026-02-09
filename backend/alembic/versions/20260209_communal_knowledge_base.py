"""Communal knowledge base: rename user_id to ingested_by, make nullable, global arxiv_id unique.

Revision ID: 012_communal_knowledge_base
Revises: 011_add_user_tiers
Create Date: 2026-02-09

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012_communal_knowledge_base"
down_revision: Union[str, None] = "011_add_user_tiers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename user_id -> ingested_by and make nullable
    op.alter_column("papers", "user_id", new_column_name="ingested_by", nullable=True)

    # 2. Replace per-user unique constraint with global arxiv_id unique
    op.drop_constraint("uq_papers_user_arxiv", "papers", type_="unique")
    op.create_unique_constraint("uq_papers_arxiv_id", "papers", ["arxiv_id"])

    # 3. Rename index
    op.drop_index("ix_papers_user_id", table_name="papers")
    op.create_index("ix_papers_ingested_by", "papers", ["ingested_by"])

    # 4. Rename foreign key
    op.drop_constraint("fk_papers_user_id", "papers", type_="foreignkey")
    op.create_foreign_key("fk_papers_ingested_by", "papers", "users", ["ingested_by"], ["id"])


def downgrade() -> None:
    # 1. Backfill NULLs so the column can become NOT NULL
    op.execute(
        "UPDATE papers SET ingested_by = (SELECT id FROM users WHERE clerk_id = 'system') "
        "WHERE ingested_by IS NULL"
    )

    # 2. Rename column back and make NOT NULL
    op.alter_column("papers", "ingested_by", new_column_name="user_id", nullable=False)

    # 3. Reverse foreign key (column is now user_id)
    op.drop_constraint("fk_papers_ingested_by", "papers", type_="foreignkey")
    op.create_foreign_key("fk_papers_user_id", "papers", "users", ["user_id"], ["id"])

    # 4. Reverse index
    op.drop_index("ix_papers_ingested_by", table_name="papers")
    op.create_index("ix_papers_user_id", "papers", ["user_id"])

    # 5. Reverse unique constraint
    op.drop_constraint("uq_papers_arxiv_id", "papers", type_="unique")
    op.create_unique_constraint("uq_papers_user_arxiv", "papers", ["user_id", "arxiv_id"])
