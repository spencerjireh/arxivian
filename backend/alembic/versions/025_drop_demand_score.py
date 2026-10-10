"""Drop paper_scores.demand_score and its evidence rows (ARX-73).

Revision ID: 025_drop_demand_score
Revises: 024_drop_dup_session_id_index
Create Date: 2026-10-10

Demand measured citation velocity, which cannot exist for a feed of papers published in
the last seven days: it averaged 20/100 while carrying 0.30 of the composite, and because
`compute_composite` renormalized over present sub-scores, a paper whose Semantic Scholar
lookup soft-failed outranked one whose lookup succeeded by ~13.6 points. 85% of the live
top 20 were failed lookups against an 18% base rate.

Downgrade restores the column as NULL for every row; the values are not recoverable
without re-scoring, which is accepted -- they were near-constant and a third were NULL.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "025_drop_demand_score"
down_revision: str | None = "024_drop_dup_session_id_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Evidence first: these rows are owned by the dimension, not the column.
    op.execute("DELETE FROM score_evidence WHERE dimension = 'demand'")
    # The v2 source of truth is the `dimensions` JSONB; drop demand's entry there too so
    # the stored payload matches the rubric the code now implements.
    op.execute("UPDATE paper_scores SET dimensions = dimensions - 'demand'")
    op.drop_column("paper_scores", "demand_score")


def downgrade() -> None:
    op.add_column("paper_scores", sa.Column("demand_score", sa.Integer(), nullable=True))
