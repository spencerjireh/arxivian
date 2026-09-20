"""Add rubric v2 columns to paper_scores: dimensions, attributes, model, input_tokens.

Revision ID: 020_add_score_dimensions
Revises: 019_add_scoring_tables
Create Date: 2026-09-19

The four `*_score` integer columns stay as derived denormalizations; `dimensions`
becomes the source of truth (per-dimension level distributions + atomic Jev judgments).
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "020_add_score_dimensions"
down_revision: str | None = "019_add_scoring_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "paper_scores",
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "paper_scores",
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("paper_scores", sa.Column("model", sa.String(length=50), nullable=True))
    op.add_column("paper_scores", sa.Column("input_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("paper_scores", "input_tokens")
    op.drop_column("paper_scores", "model")
    op.drop_column("paper_scores", "attributes")
    op.drop_column("paper_scores", "dimensions")
