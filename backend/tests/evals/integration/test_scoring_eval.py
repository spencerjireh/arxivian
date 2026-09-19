"""Golden-set accuracy gate for the Stage 2 scoring graph (SPE-272, rubric v2 / SPE-293).

Runs the real scoring graph on each seeded golden paper with real TypeSafe Jev judgments +
real retrieval (Semantic Scholar is stubbed -- demand is provisional and NOT graded), then
measures agreement against the hand labels in `tests/evals/fixtures/scoring_scenarios.py`.
Bands come from each dimension's DERIVED 0-100 score; a calibration report (confidence on
agreeing vs disagreeing papers) is printed alongside.

The HARD gate is the `implementable` binary, which is robust to adjacent-band noise (a MED
vs HIGH flip does not change it, since both satisfy `>= MED`) -- see the band-sensitivity
finding in `docs/design/scoring-rubric.md`. Per-dimension band agreement is reported but NOT
enforced while the labels are first-pass (`reviewed=False`) and demand is provisional.

`MIN_IMPLEMENTABLE_AGREEMENT` is a MEASURED baseline: pin it at/just below the first real
run's observed agreement, not a guess. Run:

    just inteval-seed              # ingests the golden papers once (idempotent)
    just inteval -k scoring -s     # -s surfaces the per-dimension diagnostics

Requires `TYPESAFE_API_KEY`; `EVAL_TYPESAFE_MODEL` overrides the configured Jev model.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

from src.clients.semantic_scholar_client import CitationMetrics
from src.config import get_settings
from src.factories.client_factories import get_typesafe_client
from src.factories.service_factories import get_ingest_service, get_search_service
from src.repositories.paper_repository import PaperRepository
from src.repositories.scoring_repository import ScoringRepository
from src.schemas.scoring_state import RUBRIC_VERSION, Band, score_to_band
from src.services.scoring_service.context import ScoringContext
from src.services.scoring_service.scoring_graph_builder import build_scoring_graph

from ..fixtures.scoring_scenarios import SCORING_SCENARIOS

# Hard gate. Pin at/just below the first `just inteval -k scoring` run's observed
# implementable-binary agreement (see module docstring). Conservative until measured.
MIN_IMPLEMENTABLE_AGREEMENT = 0.75

# The gate is only meaningful if enough golden papers actually ingested + scored. Below this,
# the seed under-ingested (network/PDF failures) and the run is not representative.
MIN_SCORED_COVERAGE = 20

# LOW < MED < HIGH, for adjacent-band tolerance + the `>= MED` implementable rule.
_BAND_RANK: dict[Band, int] = {"LOW": 0, "MED": 1, "HIGH": 2}
_MED_RANK = _BAND_RANK["MED"]


def _stub_semantic_scholar() -> AsyncMock:
    """Stub the S2 client. Demand is not graded, so return a fixed 'not found' metric --
    keeps the run hermetic and off the (rate-limited, flaky) real API."""
    stub = AsyncMock()
    stub.get_citation_metrics = AsyncMock(
        side_effect=lambda arxiv_id: CitationMetrics(arxiv_id=arxiv_id, found=False)
    )
    return stub


def _build_scoring_context(session, model: str) -> ScoringContext:
    """A production-shaped ScoringContext with real Jev + real services, S2 stubbed."""
    return ScoringContext(
        typesafe_client=get_typesafe_client(model=model),
        semantic_scholar_client=_stub_semantic_scholar(),
        ingest_service=get_ingest_service(session),
        search_service=get_search_service(session),
        paper_repository=PaperRepository(session),
        scoring_repository=ScoringRepository(session),
        db_session=session,
        rubric_version=RUBRIC_VERSION,
    )


def _band(state: dict, key: str) -> Band | None:
    """Bucket a dimension's derived 0-100 score into its band; None if the dim soft-failed."""
    result = state.get(key)
    return score_to_band(result.derived_score()) if result is not None else None


def _predicted_implementable(state: dict) -> bool | None:
    """Apply the rubric rule to the emitted scores. None if a needed dimension soft-failed."""
    method = _band(state, "method_clarity_result")
    feasibility = _band(state, "resource_feasibility_result")
    gate = state.get("data_availability_result")
    if method is None or feasibility is None or gate is None:
        return None
    data_pass = gate.level == 1
    return data_pass and _BAND_RANK[method] >= _MED_RANK and _BAND_RANK[feasibility] >= _MED_RANK


def _describe(record: dict) -> str:
    """One diagnostic line per paper: per-dimension band, expected level, confidence, and
    the atomic judgments -- what to read when tuning questions or combine rules."""
    state = record["state"]
    scenario = record["scenario"]
    parts = [f"[scoring-eval]   {scenario.id}"]
    for dim in ("method_clarity", "resource_feasibility", "data_availability"):
        result = state.get(f"{dim}_result")
        if result is None:
            parts.append(f"{dim}=soft-failed")
            continue
        golden = getattr(scenario, dim)
        judgments = " ".join(
            f"{j.key}={j.probabilities.get('yes', j.answer)}"
            if j.kind == "noul"
            else f"{j.key}={j.answer}"
            for j in result.judgments
        )
        parts.append(
            f"{dim}: pred={result.band()} gold={golden} expected={result.expected:.2f} "
            f"conf={result.confidence:.2f} [{judgments}]"
        )
    return " | ".join(parts)


@pytest.fixture(scope="session")
async def scoring_results(session_factory) -> list[dict]:
    """Score every seeded golden paper once; return one record per scenario.

    Reads the four `*_result` off the returned graph state directly -- no DB round-trip
    (the run is rolled back). Scenarios whose paper did not seed are marked unscored.
    Per-paper Jev input tokens are collected for the cost report.
    """
    model = os.environ.get("EVAL_TYPESAFE_MODEL") or get_settings().typesafe_model
    graph = build_scoring_graph()

    records: list[dict] = []
    for scenario in SCORING_SCENARIOS:
        async with session_factory() as session:
            paper = await PaperRepository(session).get_by_arxiv_id(scenario.arxiv_id)
            if paper is None or not paper.pdf_processed:
                records.append({"scenario": scenario, "scored": False, "state": None})
                continue
            context = _build_scoring_context(session, model)
            try:
                state = await graph.ainvoke(
                    {"arxiv_id": scenario.arxiv_id, "rubric_version": RUBRIC_VERSION},
                    {"configurable": {"context": context}},
                )
                tokens = sum(
                    (state.get(k) or {}).get("input_tokens") or 0
                    for k in (
                        "method_clarity_usage",
                        "resource_feasibility_usage",
                        "data_availability_usage",
                    )
                )
                records.append(
                    {"scenario": scenario, "scored": True, "state": state, "input_tokens": tokens}
                )
            except Exception as exc:  # noqa: BLE001 -- a bad paper skips, not fails the suite
                records.append(
                    {"scenario": scenario, "scored": False, "state": None, "error": str(exc)}
                )
            finally:
                await session.rollback()
    return records


def _scored(records: list[dict]) -> list[dict]:
    return [r for r in records if r["scored"]]


def test_scoring_coverage(scoring_results: list[dict]) -> None:
    """Enough golden papers must have ingested + scored for the gate to mean anything."""
    scored = _scored(scoring_results)
    assert len(scored) >= MIN_SCORED_COVERAGE, (
        f"Only {len(scored)}/{len(SCORING_SCENARIOS)} golden papers scored -- the seed "
        "under-ingested. Run `just inteval-seed` and check for PDF/network failures."
    )


def test_implementable_agreement(scoring_results: list[dict]) -> None:
    """HARD GATE: predicted `implementable` must agree with the hand labels at >= threshold."""
    matches = 0
    total = 0
    mismatches: list[str] = []
    for record in _scored(scoring_results):
        predicted = _predicted_implementable(record["state"])
        if predicted is None:  # a required dimension soft-failed -- not gradable
            continue
        total += 1
        golden = record["scenario"].implementable
        if predicted == golden:
            matches += 1
        else:
            mismatches.append(f"{record['scenario'].id}(gold={golden}, pred={predicted})")
            print(_describe(record))

    agreement = matches / total if total else 0.0
    summary = (
        f"[scoring-eval] implementable agreement: {matches}/{total} = {agreement:.1%} "
        f"(threshold {MIN_IMPLEMENTABLE_AGREEMENT:.0%}); mismatches: {mismatches or 'none'}"
    )
    print(summary)

    assert total >= MIN_SCORED_COVERAGE, (
        f"Only {total} papers were gradable (needed {MIN_SCORED_COVERAGE}). {summary}"
    )
    assert agreement >= MIN_IMPLEMENTABLE_AGREEMENT, summary


@pytest.mark.parametrize(
    "dimension,result_key",
    [
        ("method_clarity", "method_clarity_result"),
        ("resource_feasibility", "resource_feasibility_result"),
    ],
)
def test_dimension_band_agreement_report(
    scoring_results: list[dict], dimension: str, result_key: str
) -> None:
    """DIAGNOSTIC (not gated): report exact + adjacent-tolerant per-dimension band agreement.

    Not enforced while labels are `reviewed=False`; it exists to inform tuning and the
    eventual per-dimension gate once labels are signed off. Run with `-s` to see it.
    """
    exact = 0
    adjacent = 0
    total = 0
    for record in _scored(scoring_results):
        predicted = _band(record["state"], result_key)
        if predicted is None:
            continue
        golden: Band = getattr(record["scenario"], dimension)
        total += 1
        if predicted == golden:
            exact += 1
        if abs(_BAND_RANK[predicted] - _BAND_RANK[golden]) <= 1:
            adjacent += 1

    exact_pct = exact / total if total else 0.0
    adj_pct = adjacent / total if total else 0.0
    print(
        f"[scoring-eval] {dimension}: exact {exact}/{total} = {exact_pct:.1%}, "
        f"adjacent-tolerant {adjacent}/{total} = {adj_pct:.1%}"
    )
    assert total > 0, f"No papers produced a {dimension} band (all soft-failed?)."


def test_calibration_report(scoring_results: list[dict]) -> None:
    """DIAGNOSTIC (not gated): is Jev less confident when it disagrees with the labels?

    Per paper, confidence = the minimum over the three judged dimensions (the weakest
    link decides whether the card deserves a low-confidence marker). Reports the mean
    confidence on papers whose `implementable` prediction agrees vs disagrees with the
    label, plus per-dimension means and total Jev input tokens. Run with `-s` to see it.
    """
    agree: list[float] = []
    disagree: list[float] = []
    per_dim: dict[str, list[float]] = {
        "method_clarity": [],
        "resource_feasibility": [],
        "data_availability": [],
    }
    total_tokens = 0
    for record in _scored(scoring_results):
        state = record["state"]
        total_tokens += record.get("input_tokens") or 0
        results = {dim: state.get(f"{dim}_result") for dim in per_dim}
        if any(r is None for r in results.values()):
            continue
        for dim, result in results.items():
            per_dim[dim].append(result.confidence)
        conf = min(r.confidence for r in results.values())
        predicted = _predicted_implementable(state)
        (agree if predicted == record["scenario"].implementable else disagree).append(conf)

    def _mean(xs: list[float]) -> str:
        return f"{sum(xs) / len(xs):.2f} (n={len(xs)})" if xs else "n/a"

    print(
        f"[scoring-eval] calibration: mean min-confidence agree {_mean(agree)}, "
        f"disagree {_mean(disagree)}; per-dimension "
        + ", ".join(f"{dim} {_mean(v)}" for dim, v in per_dim.items())
        + f"; total Jev input tokens {total_tokens}"
    )
    assert agree or disagree, "No gradable papers for the calibration report."
