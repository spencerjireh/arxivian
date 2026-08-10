"""Digest snapshot schema (Stage 3, SPE-271).

`build_digest_task` writes a cached candidate ranking snapshot per week + category set
(`models/digest.py`). Each entry is one paper's global sub-scores plus a provisional
composite used only as the bake-time default order -- the per-user weighted composite and
compute-profile match are applied at read time (SPE-274). See `docs/design/scoring-rubric.md`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Provisional composite weights (proposed default in `docs/design/scoring-rubric.md`). The
# data-availability gate is applied by selection (only PASS papers enter a digest), so it is
# a constant 1 here and omitted from the formula.
_METHOD_WEIGHT = 0.35
_FEASIBILITY_WEIGHT = 0.35
_DEMAND_WEIGHT = 0.30


def compute_provisional_composite(
    method_clarity_score: int | None,
    resource_feasibility_score: int | None,
    demand_score: int | None,
) -> float:
    """Weighted sub-score sum for the bake-time default order (null sub-scores count as 0).

    Provisional only: read time recomputes with per-user weights + compute-profile match.
    """
    method = method_clarity_score or 0
    feasibility = resource_feasibility_score or 0
    demand = demand_score or 0
    return round(
        _METHOD_WEIGHT * method + _FEASIBILITY_WEIGHT * feasibility + _DEMAND_WEIGHT * demand,
        2,
    )


class DigestRankingEntry(BaseModel):
    """One paper's row in a digest's `ranking` snapshot (stored as JSONB)."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str = Field(..., description="UUID string of the scored paper")
    arxiv_id: str
    title: str
    method_clarity_score: int | None
    resource_feasibility_score: int | None
    data_availability_score: int | None
    demand_score: int | None
    provisional_composite: float = Field(
        ..., description="Bake-time default order only; read time re-ranks per user"
    )
