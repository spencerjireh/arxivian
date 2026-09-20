"""Pure read-side derivations over a stored `PaperScore` row (Phase 2, SPE-274).

The feed and the paper-detail endpoint share one vocabulary: the derived 0-100 sub-scores,
a read-time composite, a template verdict line, the signal chips, and a low-confidence
marker. Everything here is pure -- no I/O -- so the routers and the digest task can reuse
it. The verdict is composed in code from the Jev judgments (task type, model family,
compute tier, data access); no LLM call is made at read time. See
`docs/product/feed-prd.md` section 4 and `docs/design/scoring-rubric.md`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from src.schemas.feed import FeedScores, FeedSignals
from src.schemas.papers import DimensionDetail, EvidenceItem, PaperAttributesDetail
from src.services.feed_service.digest import DEFAULT_WEIGHTS, CompositeWeights, compute_composite
from src.services.scoring_service.state import DimensionScore, Judgment
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.models.paper_score import PaperScore

log = get_logger(__name__)

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
