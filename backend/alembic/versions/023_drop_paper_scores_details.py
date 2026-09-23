"""Drop paper_scores.details (ARX-37).

Revision ID: 023_drop_paper_scores_details
Revises: 022_drop_chat_first_leftovers
Create Date: 2026-09-21

`details` held v1 audit metadata ({dimension: {reasoning, model}}). Rubric v2 stores the
judgments themselves in `dimensions`, and nothing has written `details` since; the
repository kwarg was removed in #49. Downgrade re-adds the nullable column, empty.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "023_drop_paper_scores_details"
down_revision: str | None = "022_drop_chat_first_leftovers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("paper_scores", "details")


def downgrade() -> None:
    op.add_column(
        "paper_scores",
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
