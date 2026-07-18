"""Add scoring pipeline tables: paper_scores, score_evidence, user_paper_states, digests.

Revision ID: 019_add_scoring_tables
Revises: 018_add_conversation_title
Create Date: 2026-07-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "019_add_scoring_tables"
down_revision: Union[str, None] = "018_add_conversation_title"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the four scoring tables."""
    # paper_scores -- global per-dimension sub-scores per paper + rubric version.
    op.create_table(
        "paper_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "paper_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("papers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rubric_version", sa.String(20), nullable=False, server_default="v1"),
        sa.Column("method_clarity_score", sa.Integer, nullable=True),
        sa.Column("resource_feasibility_score", sa.Integer, nullable=True),
        sa.Column("data_availability_score", sa.Integer, nullable=True),
        sa.Column("demand_score", sa.Integer, nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("paper_id", "rubric_version", name="uq_paper_scores_paper_rubric"),
    )
    op.create_index("ix_paper_scores_paper_id", "paper_scores", ["paper_id"])

    # score_evidence -- first-class quoted spans / external hits per sub-score.
    op.create_table(
        "score_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "paper_score_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("paper_scores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dimension", sa.String(50), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_score_evidence_paper_score_id", "score_evidence", ["paper_score_id"])

    # user_paper_states -- per-user lifecycle state for a paper.
    op.create_table(
        "user_paper_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "paper_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("papers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(20), nullable=False, server_default="saved"),
        sa.Column("repo_url", sa.Text, nullable=True),
        sa.Column("dismissal_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "paper_id", name="uq_user_paper_states_user_paper"),
    )
    op.create_index("ix_user_paper_states_user_id", "user_paper_states", ["user_id"])
    op.create_index("ix_user_paper_states_paper_id", "user_paper_states", ["paper_id"])

    # digests -- cached candidate ranking snapshot per week + category set.
    op.create_table(
        "digests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column("category_key", sa.String(255), nullable=False),
        sa.Column("categories", postgresql.JSONB, nullable=False),
        sa.Column("ranking", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("week_start", "category_key", name="uq_digests_week_category"),
    )
    op.create_index("ix_digests_week_start", "digests", ["week_start"])


def downgrade() -> None:
    """Drop the four scoring tables (children before parents)."""
    op.drop_index("ix_digests_week_start", table_name="digests")
    op.drop_table("digests")

    op.drop_index("ix_user_paper_states_paper_id", table_name="user_paper_states")
    op.drop_index("ix_user_paper_states_user_id", table_name="user_paper_states")
    op.drop_table("user_paper_states")

    op.drop_index("ix_score_evidence_paper_score_id", table_name="score_evidence")
    op.drop_table("score_evidence")

    op.drop_index("ix_paper_scores_paper_id", table_name="paper_scores")
    op.drop_table("paper_scores")
