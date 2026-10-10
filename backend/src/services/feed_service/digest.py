"""Digest snapshot schema (Stage 3, ARX-7).

`build_digest_task` writes a cached candidate ranking snapshot per week + category set
(`models/digest.py`). Each entry is one paper's global sub-scores plus a provisional
composite used only as the bake-time default order -- the per-user weighted composite and
compute-profile match are applied at read time (ARX-10). See `ARX-56`.
"""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, ConfigDict, Field


def week_start_for(day: date) -> date:
    """Monday of `day`'s ISO week (the `digests.week_start` key)."""
    return day - timedelta(days=day.weekday())


def category_key_for(categories: list[str]) -> str:
    """Stable key for a category set (matches the `digests` unique constraint)."""
    return ",".join(sorted(categories))


class CompositeWeights(BaseModel):
    """Weights over the two scored sub-dimensions.

    The data-availability gate is applied by selection (only PASS papers enter a digest),
    so it is a constant 1 and omitted from the formula. Per-user weights (ARX-9) reuse
    this shape.

    Demand was removed in ARX-73. It was 0.35/0.35/0.30 before; the two survivors were
    already equal, so 0.5/0.5 preserves the relative order of any two papers and the only
    ranking change is demand's distortion going away.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    method_clarity: float = Field(0.5, ge=0.0)
    resource_feasibility: float = Field(0.5, ge=0.0)


DEFAULT_WEIGHTS = CompositeWeights()


def compute_composite(
    method_clarity_score: int | None,
    resource_feasibility_score: int | None,
    *,
    weights: CompositeWeights = DEFAULT_WEIGHTS,
) -> float:
    """Weighted mean over the sub-scores that are present; weights renormalize to 1.

    A NULL sub-score is excluded rather than counted as 0, so a paper is not penalized for
    a judgment that happened to soft-fail. All NULL -> 0.0.
    """
    pairs = (
        (method_clarity_score, weights.method_clarity),
        (resource_feasibility_score, weights.resource_feasibility),
    )
    present = [(score, weight) for score, weight in pairs if score is not None]
    total_weight = sum(weight for _, weight in present)
    if total_weight <= 0:
        return 0.0
    return round(sum(score * weight for score, weight in present) / total_weight, 2)


def compute_provisional_composite(
    method_clarity_score: int | None,
    resource_feasibility_score: int | None,
) -> float:
    """Bake-time default order with the default weights (see `compute_composite`)."""
    return compute_composite(method_clarity_score, resource_feasibility_score)


class DigestRankingEntry(BaseModel):
    """One paper's row in a digest's `ranking` snapshot (stored as JSONB).

    Unknown keys are IGNORED, not forbidden. `FeedService._enrich` validates every stored
    entry and merely logs on failure, so a field removed from this model would silently
    drop every already-persisted paper from the feed rather than fail loudly -- which is
    exactly what dropping `demand_score` would have done in ARX-73. Tolerance keeps a stale
    field harmless; the digest rebuild is what actually cleans the rows up.
    """

    model_config = ConfigDict(extra="ignore")

    paper_id: str = Field(..., description="UUID string of the scored paper")
    arxiv_id: str
    title: str
    method_clarity_score: int | None
    resource_feasibility_score: int | None
    data_availability_score: int | None
    provisional_composite: float = Field(
        ..., description="Bake-time default order only; read time re-ranks per user"
    )
