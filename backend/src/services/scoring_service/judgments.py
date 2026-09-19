"""Combine rules: atomic Jev answers -> per-dimension level distributions.

Pure functions, no I/O. Each dimension node asks its questions, then hands the normalized
answers here to build a `DimensionScore`. Keeping the arithmetic separate from the nodes
keeps it unit-testable and makes the rubric tunable without re-running inference.
"""

from __future__ import annotations

from typing import Sequence

from src.clients.typesafe_client import ChoiceResult, ScoreResult
from src.schemas.scoring_state import (
    DEMAND_LEVELS,
    DIMENSION_MAX_LEVEL,
    DimensionScore,
    EvidenceSpan,
    Judgment,
)


def poisson_binomial(probs: Sequence[float]) -> dict[int, float]:
    """P(k successes) for independent Bernoulli(p_i), k = 0..len(probs). Exact DP."""
    dist = [1.0]
    for p in probs:
        nxt = [0.0] * (len(dist) + 1)
        for k, mass in enumerate(dist):
            nxt[k] += mass * (1.0 - p)
            nxt[k + 1] += mass * p
        dist = nxt
    return {k: round(v, 6) for k, v in enumerate(dist)}


def argmax(dist: dict[int, float]) -> int:
    """Highest-probability level; ties resolve to the lower level (conservative)."""
    return max(sorted(dist), key=lambda k: dist[k])


def noul_judgment(key: str, p_yes: float) -> Judgment:
    """A Noul is P(yes) only; the answer is the majority side and confidence its mass."""
    p_yes = min(max(p_yes, 0.0), 1.0)
    return Judgment(
        key=key,
        kind="noul",
        answer=p_yes >= 0.5,
        probabilities={"yes": round(p_yes, 4), "no": round(1.0 - p_yes, 4)},
        confidence=round(max(p_yes, 1.0 - p_yes), 4),
    )


def choice_judgment(key: str, result: ChoiceResult) -> Judgment:
    return Judgment(
        key=key,
        kind="choice",
        answer=result.choice,
        probabilities={k: round(v, 4) for k, v in result.probabilities.items()},
        confidence=round(result.confidence, 4),
    )


def score_judgment(key: str, result: ScoreResult) -> Judgment:
    return Judgment(
        key=key,
        kind="score",
        answer=argmax(result.probabilities),
        probabilities={str(k): round(v, 4) for k, v in sorted(result.probabilities.items())},
        confidence=round(result.confidence, 4),
        legend=result.legend or None,
    )


def _pct(p: float) -> str:
    return f"{p:.2f}"


# --- Method clarity: count of satisfied criteria --------------------------------------


def combine_method_clarity(
    nouls: dict[str, float],
    criteria_keys: Sequence[str],
    evidence: list[EvidenceSpan],
) -> DimensionScore:
    """Level = number of clarity criteria satisfied; distribution is the Poisson-binomial
    of the per-criterion P(yes). Expected = sum of the probabilities."""
    probs = [nouls[k] for k in criteria_keys]
    dist = poisson_binomial(probs)
    level = argmax(dist)
    summary = ", ".join(f"{k} {_pct(p)}" for k, p in zip(criteria_keys, probs))
    return DimensionScore(
        dimension="method_clarity",
        level=level,
        max_level=DIMENSION_MAX_LEVEL["method_clarity"],
        expected=round(sum(probs), 4),
        probabilities=dist,
        confidence=dist[level],
        judgments=[noul_judgment(k, p) for k, p in zip(criteria_keys, probs)],
        evidence=evidence,
        reasoning=f"{level} of {len(criteria_keys)} clarity criteria likely satisfied ({summary})",
    )


# --- Resource feasibility: one ordinal Score + auxiliary Nouls ------------------------


def combine_resource_feasibility(
    tier: ScoreResult,
    aux_nouls: dict[str, float],
    evidence: list[EvidenceSpan],
) -> DimensionScore:
    """Distribution is the compute-tier Score's own distribution. The auxiliary Nouls
    (compute stated, pretrained weights released) are recorded, not combined: a compute
    tier is a single ordinal judgment and splitting it would break the relationship.
    Dimension confidence is the mass on the argmax (uniform with the other dimensions);
    the SDK's own concentration metric stays on the `compute_tier` judgment."""
    max_level = DIMENSION_MAX_LEVEL["resource_feasibility"]
    dist = {lvl: round(tier.probabilities.get(lvl, 0.0), 6) for lvl in range(max_level + 1)}
    level = argmax(dist)
    tier_label = (
        tier.legend[level].split(":")[0]
        if tier.legend and level < len(tier.legend)
        else f"tier {level}"
    )
    aux = ", ".join(f"{k} {_pct(p)}" for k, p in aux_nouls.items())
    return DimensionScore(
        dimension="resource_feasibility",
        level=level,
        max_level=max_level,
        expected=round(tier.score, 4),
        probabilities=dist,
        confidence=dist[level],
        judgments=[score_judgment("compute_tier", tier)]
        + [noul_judgment(k, p) for k, p in aux_nouls.items()],
        evidence=evidence,
        reasoning=f"compute tier {level} ({tier_label}), expected {tier.score:.2f}; {aux}",
    )


# --- Data availability: 6-way Choice regrouped into a PASS/FAIL gate -----------------


def combine_data_availability(
    access: ChoiceResult,
    pass_options: frozenset[str],
    evidence: list[EvidenceSpan],
) -> DimensionScore:
    """Level 1 = PASS (accessible data), 0 = FAIL. Mass is summed per side; the argmax
    decides the gate so the digest's `== 100` filter is exact."""
    p_pass = sum(p for opt, p in access.probabilities.items() if opt in pass_options)
    dist = {0: round(1.0 - p_pass, 6), 1: round(p_pass, 6)}
    level = argmax(dist)
    return DimensionScore(
        dimension="data_availability",
        level=level,
        max_level=DIMENSION_MAX_LEVEL["data_availability"],
        expected=round(p_pass, 4),
        probabilities=dist,
        confidence=dist[level],
        judgments=[choice_judgment("data_access", access)],
        evidence=evidence,
        reasoning=(
            f"{'PASS' if level == 1 else 'FAIL'}: data access judged '{access.choice}' "
            f"(P(pass) {_pct(p_pass)})"
        ),
    )


# --- Demand: Semantic Scholar band as a one-hot level --------------------------------


def demand_from_band(band: str, evidence: list[EvidenceSpan], reasoning: str) -> DimensionScore:
    level = DEMAND_LEVELS[band]
    max_level = DIMENSION_MAX_LEVEL["demand"]
    dist = {lvl: 1.0 if lvl == level else 0.0 for lvl in range(max_level + 1)}
    return DimensionScore(
        dimension="demand",
        level=level,
        max_level=max_level,
        expected=float(level),
        probabilities=dist,
        confidence=1.0,
        judgments=[],
        evidence=evidence,
        reasoning=reasoning,
    )
