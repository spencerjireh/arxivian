"""Feed presentation schemas and the pure derivations behind them (Phase 2, SPE-274).

The feed and the paper-detail endpoint share one read-side vocabulary over a stored
`PaperScore` row: the derived 0-100 sub-scores, a read-time composite, a template verdict
line, the signal chips, and a low-confidence marker. Everything here is pure -- no I/O, no
service imports -- so the routers and the digest task can reuse it. The verdict is composed
in code from the Jev judgments (task type, model family, compute tier, data access); no LLM
call is made at read time. See `docs/product/feed-prd.md` section 4 and
`docs/design/scoring-rubric.md`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, model_validator

from src.schemas.digest import DEFAULT_WEIGHTS, CompositeWeights, compute_composite
from src.schemas.scoring_state import DimensionScore, Judgment
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.models.paper_score import PaperScore

log = get_logger(__name__)

PaperState = Literal["saved", "dismissed", "implementing", "shipped"]
PAPER_STATES: tuple[str, ...] = ("saved", "dismissed", "implementing", "shipped")

# Dimension order for breakdown displays.
DIMENSION_ORDER: tuple[str, ...] = (
    "method_clarity",
    "resource_feasibility",
    "data_availability",
    "demand",
)

# A dimension whose argmax mass is below this is flagged on the card rather than hidden
# (`docs/design/scoring-rubric.md`, Calibration).
LOW_CONFIDENCE_THRESHOLD = 0.5

# compute_profile -> minimum resource_feasibility level (0 cluster .. 4 laptop) that fits.
COMPUTE_PROFILE_MIN_LEVEL: dict[str, int] = {"laptop": 3, "single_gpu": 2, "cloud": 1}

# Verdict phrases per resource_feasibility level (questions.COMPUTE_TIER_LEVELS).
TIER_PHRASES: dict[int, str] = {
    4: "runs on a laptop or CPU",
    3: "one consumer GPU",
    2: "one datacenter GPU",
    1: "multi-GPU node",
    0: "cluster scale",
}

# Verdict phrases per data_access option (questions.DATA_ACCESS criteria labels).
DATA_PHRASES: dict[str, str] = {
    "public benchmark or standard dataset": "public data",
    "released by the authors": "data released by the authors",
    "synthetic or generated": "synthetic data",
    "available on request or under license": "data on request",
    "proprietary or private": "private data",
    "not stated": "data source not stated",
}

_OTHER = "other"


# ---------------------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------------------


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


class UserPaperStateResponse(BaseModel):
    """A user's lifecycle state for one paper."""

    model_config = ConfigDict(from_attributes=True)

    state: PaperState
    repo_url: str | None = None
    dismissal_reason: str | None = None
    updated_at: datetime


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


class UserPaperStateRequest(BaseModel):
    """PUT /papers/{arxiv_id}/state body."""

    model_config = ConfigDict(extra="forbid")

    state: PaperState
    repo_url: HttpUrl | None = None
    dismissal_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _check_fields_for_state(self) -> UserPaperStateRequest:
        if self.state == "shipped" and self.repo_url is None:
            raise ValueError("repo_url is required when state is 'shipped'")
        if self.state != "dismissed" and self.dismissal_reason is not None:
            raise ValueError("dismissal_reason is only allowed when state is 'dismissed'")
        return self


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


class LibraryResponse(BaseModel):
    """The caller's papers grouped by lifecycle state, newest update first. Dismissed
    papers are feedback, not library entries, and are left out."""

    saved: list[FeedItem]
    implementing: list[FeedItem]
    shipped: list[FeedItem]


# ---------------------------------------------------------------------------------------
# Pure derivations
# ---------------------------------------------------------------------------------------


def parse_dimensions(dimensions: dict[str, Any] | None) -> dict[str, DimensionScore]:
    """Rebuild `DimensionScore`s from a `paper_scores.dimensions` payload.

    Malformed entries are skipped (and logged), never raised: one bad row must not 500 the
    whole feed.
    """
    parsed: dict[str, DimensionScore] = {}
    for name, payload in (dimensions or {}).items():
        if not isinstance(payload, dict):
            continue
        try:
            parsed[name] = DimensionScore.from_jsonb(payload)
        except ValidationError as e:
            log.warning("feed_dimension_unparseable", dimension=name, error=str(e))
    return parsed


def judgment(dim: DimensionScore | None, key: str) -> Judgment | None:
    if dim is None:
        return None
    return next((j for j in dim.judgments if j.key == key), None)


def attribute(attributes: dict[str, Any] | None, key: str) -> Judgment | None:
    payload = (attributes or {}).get(key)
    if not isinstance(payload, dict):
        return None
    try:
        return Judgment.model_validate(payload)
    except ValidationError as e:
        log.warning("feed_attribute_unparseable", attribute=key, error=str(e))
        return None


def feasibility_level(dims: dict[str, DimensionScore]) -> int | None:
    dim = dims.get("resource_feasibility")
    return dim.level if dim is not None else None


def compute_match(dims: dict[str, DimensionScore], compute_profile: str | None) -> bool | None:
    """Whether the paper's compute tier fits the user's declared hardware (None = no profile)."""
    if compute_profile is None:
        return None
    level = feasibility_level(dims)
    if level is None:
        return None
    return level >= COMPUTE_PROFILE_MIN_LEVEL.get(compute_profile, 0)


def build_signals(
    dims: dict[str, DimensionScore],
    attributes: dict[str, Any] | None,
    compute_profile: str | None,
) -> FeedSignals:
    algorithm = judgment(dims.get("method_clarity"), "algorithm_given")
    data_dim = dims.get("data_availability")
    data_access = judgment(data_dim, "data_access")
    code = attribute(attributes, "code_released")
    level = feasibility_level(dims)
    return FeedSignals(
        pseudocode_present=algorithm is not None and algorithm.answer is True,
        # PASS includes the recall-biased "not stated" default; do not claim public data
        # for it.
        public_datasets=(
            data_dim is not None
            and data_dim.level == 1
            and data_access is not None
            and data_access.answer != "not stated"
        ),
        single_gpu=level is not None and level >= 2,
        code_released=code is not None and code.answer is True,
        compute_match=compute_match(dims, compute_profile),
    )


def build_verdict(dims: dict[str, DimensionScore], attributes: dict[str, Any] | None) -> str:
    """Template verdict: '<family> for <task>; <compute tier>; <data access>'."""
    family_j = attribute(attributes, "model_family")
    task_j = attribute(attributes, "task_type")
    family = str(family_j.answer) if family_j is not None else _OTHER
    task = str(task_j.answer) if task_j is not None else _OTHER

    if family != _OTHER and task != _OTHER:
        head = f"{family[0].upper()}{family[1:]} for {task}"
    elif task != _OTHER:
        head = f"Method for {task}"
    elif family != _OTHER:
        head = f"{family[0].upper()}{family[1:]}"
    else:
        head = "Method paper"

    parts = [head]
    level = feasibility_level(dims)
    if level is not None and level in TIER_PHRASES:
        parts.append(TIER_PHRASES[level])
    data_access = judgment(dims.get("data_availability"), "data_access")
    if data_access is not None and str(data_access.answer) in DATA_PHRASES:
        parts.append(DATA_PHRASES[str(data_access.answer)])
    return "; ".join(parts)


def low_confidence_dimensions(dims: dict[str, DimensionScore]) -> list[str]:
    return sorted(
        name
        for name, dim in dims.items()
        if name != "demand" and dim.confidence < LOW_CONFIDENCE_THRESHOLD
    )


def build_scores(score: PaperScore, weights: CompositeWeights = DEFAULT_WEIGHTS) -> FeedScores:
    """Derived columns plus the read-time composite (NULL sub-scores renormalize)."""
    return FeedScores(
        method_clarity=score.method_clarity_score,
        resource_feasibility=score.resource_feasibility_score,
        data_availability=score.data_availability_score,
        demand=score.demand_score,
        composite=compute_composite(
            score.method_clarity_score,
            score.resource_feasibility_score,
            score.demand_score,
            weights=weights,
        ),
    )


def resolve_weights(raw: dict[str, float] | None) -> CompositeWeights:
    """Per-user weights if they validate against the default key set, else the defaults."""
    if not raw:
        return DEFAULT_WEIGHTS
    try:
        return CompositeWeights.model_validate(raw)
    except ValidationError:
        return DEFAULT_WEIGHTS


def build_dimension_details(
    dims: dict[str, DimensionScore], evidence_rows: list[Any]
) -> list[DimensionDetail]:
    """Breakdown rows in rubric order, each paired with its `score_evidence` spans."""
    by_dimension: dict[str, list[EvidenceItem]] = {}
    for row in evidence_rows:
        by_dimension.setdefault(row.dimension, []).append(EvidenceItem.model_validate(row))

    details: list[DimensionDetail] = []
    for name in DIMENSION_ORDER:
        dim = dims.get(name)
        if dim is None:
            continue
        details.append(
            DimensionDetail(
                dimension=name,
                band=dim.band(),
                score=dim.derived_score(),
                level=dim.level,
                max_level=dim.max_level,
                expected=dim.expected,
                probabilities=dim.probabilities,
                confidence=dim.confidence,
                judgments=dim.judgments,
                evidence=by_dimension.get(name, []),
                reasoning=dim.reasoning,
            )
        )
    return details


def build_attributes_detail(
    attributes: dict[str, Any] | None, evidence_rows: list[Any]
) -> PaperAttributesDetail:
    return PaperAttributesDetail(
        code_released=attribute(attributes, "code_released"),
        task_type=attribute(attributes, "task_type"),
        model_family=attribute(attributes, "model_family"),
        code_evidence=[
            EvidenceItem.model_validate(row)
            for row in evidence_rows
            if row.dimension == "code_released"
        ],
    )
