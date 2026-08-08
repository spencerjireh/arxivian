"""Repository for persisting Stage 2 scoring results.

Writes `paper_scores` (one row per `(paper_id, rubric_version)`) plus its owned
`score_evidence` rows. `upsert_score` is idempotent: a re-score under the same rubric
updates the existing row and replaces its evidence (via the `cascade="all, delete-orphan"`
relationship on `PaperScore.evidence`), so Celery retries and re-runs converge.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.paper_score import PaperScore, ScoreEvidence
from src.utils.logger import get_logger

log = get_logger(__name__)


class ScoringRepository:
    """Persists paper scores + evidence with upsert-on-rubric semantics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_score(
        self,
        *,
        paper_id: str,
        rubric_version: str,
        scores: dict[str, int | None],
        details: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> PaperScore:
        """Insert or update the `(paper_id, rubric_version)` score and replace its evidence.

        Args:
            paper_id: UUID string of the paper.
            rubric_version: Rubric revision these scores encode.
            scores: Per-dimension columns, e.g. {"method_clarity_score": 80, ...}. None
                values persist as NULL (a soft-failed dimension).
            details: Per-dimension audit metadata stored in the JSONB `details` column.
            evidence: Rows to (re)create, each {dimension, kind, text, source}.

        Returns:
            The persisted PaperScore (flushed, not committed -- the caller owns commit).
        """
        pid = uuid.UUID(paper_id)
        stmt = (
            select(PaperScore)
            .where(
                PaperScore.paper_id == pid,
                PaperScore.rubric_version == rubric_version,
            )
            .options(selectinload(PaperScore.evidence))
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()

        if existing is None:
            score = PaperScore(
                paper_id=pid,
                rubric_version=rubric_version,
                details=details,
                **scores,
            )
            self.session.add(score)
        else:
            score = existing
            for column, value in scores.items():
                setattr(score, column, value)
            score.details = details
            # Clear old evidence first; delete-orphan removes the rows on flush.
            score.evidence = []
            await self.session.flush()

        score.evidence = [
            ScoreEvidence(
                dimension=e["dimension"],
                kind=e["kind"],
                text=e["text"],
                source=e.get("source"),
            )
            for e in evidence
        ]
        await self.session.flush()

        log.info(
            "paper_score_upserted",
            paper_id=paper_id,
            rubric_version=rubric_version,
            evidence_count=len(evidence),
            created=existing is None,
        )
        return score
