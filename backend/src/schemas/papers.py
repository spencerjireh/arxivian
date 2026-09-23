"""GET /papers/{arxiv_id}/score schemas (routers/papers.py)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field

from src.schemas.base import ResponseModel
from src.schemas.feed import FeedPaper, FeedScores
from src.schemas.paper_states import UserPaperStateResponse
from src.services.scoring_service.state import Judgment, ScoreDimension


class EvidenceItem(ResponseModel):
    """One quoted span from `score_evidence`."""

    model_config = ConfigDict(from_attributes=True)

    kind: str
    text: str
    source: str | None = None


class DimensionDetail(ResponseModel):
    """One rubric dimension for the breakdown: distribution, judgments, and its evidence."""

    dimension: ScoreDimension
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


class PaperAttributesDetail(ResponseModel):
    """Product attributes (chips) plus the code-mention spans behind `code_released`."""

    code_released: Judgment | None = None
    task_type: Judgment | None = None
    model_family: Judgment | None = None
    code_evidence: list[EvidenceItem] = Field(default_factory=list)


class PaperMetadata(FeedPaper):
    """FeedPaper plus the abstract: the detail header and the 202 body."""

    abstract: str


class PaperScoreDetailResponse(ResponseModel):
    """GET /papers/{arxiv_id}/score when the paper is scored."""

    paper: PaperMetadata
    rubric_version: str
    scored_at: datetime
    scores: FeedScores
    headline: str
    meta: list[str]
    compute_match: bool | None
    low_confidence: list[ScoreDimension]
    state: UserPaperStateResponse | None
    attributes: PaperAttributesDetail
    dimensions: list[DimensionDetail]


class ScorePendingResponse(ResponseModel):
    """GET /papers/{arxiv_id}/score (202) while the paper is unscored.

    A signed-in caller has on-demand scoring running (`task_id`); an anonymous caller gets
    the metadata only, with `task_id` None, since nothing is enqueued for them.
    """

    status: Literal["pending"] = "pending"
    arxiv_id: str
    paper: PaperMetadata
    task_id: str | None = Field(
        default=None, description="None for anonymous callers: nothing was enqueued"
    )
