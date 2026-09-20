"""GET /papers/{arxiv_id}/score schemas (routers/papers.py)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.feed import FeedPaper, FeedScores, FeedSignals
from src.schemas.paper_states import UserPaperStateResponse
from src.services.scoring_service.state import Judgment


class EvidenceItem(BaseModel):
    """One quoted span from `score_evidence`."""

    model_config = ConfigDict(from_attributes=True)

    kind: str
    text: str
    source: str | None = None


class DimensionDetail(BaseModel):
    """One rubric dimension for the breakdown: distribution, judgments, and its evidence."""

    dimension: str
    band: Literal["LOW", "MED", "HIGH"]
    score: int
    level: int
    max_level: int
    expected: float
    probabilities: dict[int, float]
    confidence: float
    judgments: list[Judgment]
    evidence: list[EvidenceItem]
    reasoning: str


class PaperAttributesDetail(BaseModel):
    """Product attributes (chips) plus the code-mention spans behind `code_released`."""

    code_released: Judgment | None = None
    task_type: Judgment | None = None
    model_family: Judgment | None = None
    code_evidence: list[EvidenceItem] = Field(default_factory=list)


class PaperScoreDetailResponse(BaseModel):
    """GET /papers/{arxiv_id}/score when the paper is scored."""

    paper: FeedPaper
    rubric_version: str
    scored_at: datetime
    scores: FeedScores
    verdict: str
    signals: FeedSignals
    low_confidence: list[str]
    state: UserPaperStateResponse | None
    attributes: PaperAttributesDetail
    dimensions: list[DimensionDetail]


class ScorePendingResponse(BaseModel):
    """GET /papers/{arxiv_id}/score (202) while ingest + scoring runs on demand."""

    status: Literal["pending"] = "pending"
    arxiv_id: str
    task_id: str | None = None
