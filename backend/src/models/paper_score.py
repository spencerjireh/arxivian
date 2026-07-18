"""Paper scoring models for the implementability scoring pipeline.

`PaperScore` holds the global per-dimension sub-scores for a paper under a rubric version
(no stored composite -- the user-weighted composite is computed at read time).
`ScoreEvidence` holds the first-class quoted spans / external hits that justify each
sub-score, powering the auditable UI breakdown. See `docs/design/scoring-pipeline.md` and
`docs/design/scoring-rubric.md`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, ForeignKey, TIMESTAMP, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class PaperScore(Base):
    """Global per-dimension implementability sub-scores for a paper (one row per rubric version)."""

    __tablename__ = "paper_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        index=True,
    )
    rubric_version: Mapped[str] = mapped_column(String(20), server_default="v1")

    # Per-dimension sub-scores, 0-100. Nullable so a paper can be partially scored -- demand
    # stays null until Semantic Scholar lands (Phase 1); data availability uses 0/100 as its
    # gate flag. No code_gap_score in v1 (added in v1.1 alongside the github_search node).
    method_clarity_score: Mapped[int | None] = mapped_column(Integer)
    resource_feasibility_score: Mapped[int | None] = mapped_column(Integer)
    data_availability_score: Mapped[int | None] = mapped_column(Integer)
    demand_score: Mapped[int | None] = mapped_column(Integer)

    # Per-dimension audit metadata ({dimension: {reasoning, model}}); NOT the queryable number.
    details: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Owned evidence records
    evidence: Mapped[list[ScoreEvidence]] = relationship(
        "ScoreEvidence",
        back_populates="score",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("paper_id", "rubric_version", name="uq_paper_scores_paper_rubric"),
    )

    def __repr__(self):
        return f"<PaperScore(paper_id='{self.paper_id}', rubric='{self.rubric_version}')>"


class ScoreEvidence(Base):
    """A single quoted span (or external hit) supporting one dimension's sub-score."""

    __tablename__ = "score_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_scores.id", ondelete="CASCADE"),
        index=True,
    )
    dimension: Mapped[str] = mapped_column(String(50))
    kind: Mapped[str] = mapped_column(String(20))  # pseudocode / compute / dataset / citation
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationship to the parent score
    score: Mapped[PaperScore] = relationship("PaperScore", back_populates="evidence")

    def __repr__(self):
        return f"<ScoreEvidence(dimension='{self.dimension}', kind='{self.kind}')>"
