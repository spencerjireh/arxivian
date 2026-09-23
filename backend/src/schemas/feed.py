"""GET /feed and GET /users/me/library response schemas (routers/feed.py, paper_states.py).

The derivations that fill these cards (composite, headline, meta line, compute match,
confidence marker) live in `services/feed_service/derive.py`. `GET /feed` is public: an
anonymous caller gets the same cards with `state` and `compute_match` unset.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import ConfigDict, Field

from src.schemas.base import ResponseModel
from src.schemas.paper_states import UserPaperStateResponse
from src.services.scoring_service.state import ScoreDimension


class FeedPaper(ResponseModel):
    """Paper identity as shown on a card."""

    model_config = ConfigDict(from_attributes=True)

    arxiv_id: str
    title: str
    authors: list[str]
    categories: list[str]
    published_date: datetime
    pdf_url: str


class FeedScores(ResponseModel):
    """Derived per-dimension 0-100 sub-scores plus the read-time composite."""

    method_clarity: int | None
    resource_feasibility: int | None
    data_availability: int | None
    demand: int | None
    composite: float


class FeedItem(ResponseModel):
    """One card. The feed only emits scored papers; the library also carries papers whose
    score is missing (rubric bump, ops delete), so the score-derived fields are optional."""

    paper: FeedPaper
    scores: FeedScores | None = None
    headline: str | None = Field(
        default=None, description="'<Model family> for <task type>' from the stored attributes"
    )
    meta: list[str] = Field(
        default_factory=list,
        description="Ordered truthy-only phrases: compute tier, data access, code, weights, "
        "pseudocode, hyperparameters. Never a negative claim.",
    )
    compute_match: bool | None = Field(
        default=None, description="None when the caller has no compute profile (or is anonymous)"
    )
    low_confidence: list[ScoreDimension] = Field(
        default_factory=list, description="Dimensions whose confidence is below the threshold"
    )
    keyword_match: bool = False
    state: UserPaperStateResponse | None = None
    scored_at: datetime | None = None


class AvailableWeek(ResponseModel):
    week_start: date
    paper_count: int


class FeedResponse(ResponseModel):
    """A page of the ranked feed for one digest week."""

    week_start: date | None = Field(
        default=None, description="None when no digest has been built yet"
    )
    available_weeks: list[AvailableWeek]
    categories_available: list[str]
    total: int
    offset: int
    limit: int
    items: list[FeedItem]


class LibraryResponse(ResponseModel):
    """The caller's papers grouped by lifecycle state, newest update first. Dismissed
    papers are feedback, not library entries, and are left out."""

    saved: list[FeedItem]
    implementing: list[FeedItem]
    shipped: list[FeedItem]
