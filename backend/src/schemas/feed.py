"""GET /feed and GET /users/me/library response schemas (routers/feed.py, paper_states.py).

The derivations that fill these cards (composite, verdict, chips, confidence marker) live
in `services/feed_service/derive.py`.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.paper_states import UserPaperStateResponse


class FeedPaper(BaseModel):
    """Paper identity as shown on a card."""

    model_config = ConfigDict(from_attributes=True)

    arxiv_id: str
    title: str
    authors: list[str]
    categories: list[str]
    published_date: datetime
    pdf_url: str


class FeedScores(BaseModel):
    """Derived per-dimension 0-100 sub-scores plus the read-time composite."""

    method_clarity: int | None
    resource_feasibility: int | None
    data_availability: int | None
    demand: int | None
    composite: float


class FeedSignals(BaseModel):
    """Boolean chips. Only truthy ones render; there is never a negative 'no code' chip."""

    pseudocode_present: bool
    public_datasets: bool
    single_gpu: bool
    code_released: bool
    compute_match: bool | None = Field(
        default=None, description="None when the user has no compute profile"
    )


class FeedItem(BaseModel):
    """One card. The feed only emits scored papers; the library also carries papers whose
    score is missing (rubric bump, ops delete), so the score-derived fields are optional."""

    paper: FeedPaper
    scores: FeedScores | None = None
    verdict: str | None = None
    signals: FeedSignals | None = None
    low_confidence: list[str] = Field(
        default_factory=list, description="Dimensions whose confidence is below the threshold"
    )
    keyword_match: bool = False
    state: UserPaperStateResponse | None = None
    scored_at: datetime | None = None


class AvailableWeek(BaseModel):
    week_start: date
    paper_count: int


class FeedResponse(BaseModel):
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


class LibraryResponse(BaseModel):
    """The caller's papers grouped by lifecycle state, newest update first. Dismissed
    papers are feedback, not library entries, and are left out."""

    saved: list[FeedItem]
    implementing: list[FeedItem]
    shipped: list[FeedItem]
