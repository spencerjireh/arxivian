"""The four v1 dimension nodes + their pure helpers.

Two dimensions are LLM judgments on the strong model (method clarity, resource
feasibility); one is a deterministic keyword gate (data availability); one is a Semantic
Scholar lookup (demand). Every node SOFT-FAILS: on error it returns its result key as
`None`, so the column persists NULL and the rest of the paper still scores.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from langchain_core.runnables import RunnableConfig

from src.schemas.scoring_state import DimensionScore, EvidenceSpan, PaperScoreState
from src.services.scoring_service.prompts import (
    get_method_clarity_prompt,
    get_resource_feasibility_prompt,
)
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.services.scoring_service.context import ScoringContext

log = get_logger(__name__)

# --- Data-availability gate --------------------------------------------------------------
# Default PASS (recall-biased): FAIL only on an explicit proprietary/inaccessible signal.
PROPRIETARY_SIGNALS: tuple[str, ...] = (
    "proprietary",
    "private dataset",
    "internal dataset",
    "in-house",
    "confidential",
    "clinical",
    "patient",
    "medical record",
    "not publicly available",
    "not available to the public",
    "under license",
    "licensed dataset",
    "restricted access",
)

# --- Demand band -> score ---------------------------------------------------------------
DEMAND_BAND_TO_SCORE: dict[str, int] = {"HIGH": 85, "MED": 55, "LOW": 20}


def classify_data_gate(dataset_spans: list[str]) -> tuple[int, str | None]:
    """Return (gate_score, matched_signal). 100 = PASS, 0 = FAIL. Default PASS."""
    haystack = " ".join(dataset_spans).lower()
    for signal in PROPRIETARY_SIGNALS:
        if signal in haystack:
            return 0, signal
    return 100, None


async def _run_llm_dimension(
    context: ScoringContext,
    state: PaperScoreState,
    get_prompt: Callable[[dict, dict], tuple[str, str]],
    result_key: str,
) -> dict:
    """Shared LLM-judge path for method clarity / resource feasibility (soft-fail)."""
    arxiv_id = state["arxiv_id"]
    try:
        system, user = get_prompt(state["extracted_spans"], state["paper_meta"])
        # The client is built with scoring_strong_model, so no per-call override is needed.
        result = await context.llm_client.generate_structured(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=DimensionScore,
        )
        return {result_key: result}
    except Exception as e:
        log.warning(
            "scoring_dimension_failed", dimension=result_key, arxiv_id=arxiv_id, error=str(e)
        )
        return {result_key: None}


async def score_method_clarity_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context: ScoringContext = config["configurable"]["context"]
    return await _run_llm_dimension(
        context, state, get_method_clarity_prompt, "method_clarity_result"
    )


async def score_resource_feasibility_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context: ScoringContext = config["configurable"]["context"]
    return await _run_llm_dimension(
        context, state, get_resource_feasibility_prompt, "resource_feasibility_result"
    )


async def score_data_availability_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    arxiv_id = state["arxiv_id"]
    try:
        dataset_spans = state["extracted_spans"].get("dataset") or []
        score, matched = classify_data_gate(dataset_spans)
        evidence = [
            EvidenceSpan(text=span[:600], kind="dataset", source="retrieved")
            for span in dataset_spans[:2]
        ]
        reasoning = (
            f"Proprietary/inaccessible-data signal found ('{matched}') -- gate FAILS."
            if score == 0
            else "No proprietary-data signal in the retrieved dataset spans; data treated "
            "as accessible (gate PASSES)."
        )
        return {
            "data_availability_result": DimensionScore(
                dimension="data_availability", score=score, evidence=evidence, reasoning=reasoning
            )
        }
    except Exception as e:
        log.warning(
            "scoring_dimension_failed",
            dimension="data_availability_result",
            arxiv_id=arxiv_id,
            error=str(e),
        )
        return {"data_availability_result": None}


async def score_demand_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context: ScoringContext = config["configurable"]["context"]
    arxiv_id = state["arxiv_id"]
    try:
        metrics = await context.semantic_scholar_client.get_citation_metrics(arxiv_id)
        score = DEMAND_BAND_TO_SCORE[metrics.demand_band]
        evidence = [
            EvidenceSpan(
                text=(
                    f"{metrics.citation_count} citations "
                    f"({metrics.influential_citation_count} influential), "
                    f"{metrics.citations_per_month} citations/month (band {metrics.demand_band})"
                ),
                kind="citation",
                source="Semantic Scholar",
            )
        ]
        reasoning = (
            f"Citation velocity {metrics.citations_per_month}/month maps to band "
            f"{metrics.demand_band} -> demand {score}."
        )
        return {
            "demand_result": DimensionScore(
                dimension="demand", score=score, evidence=evidence, reasoning=reasoning
            )
        }
    except Exception as e:
        log.warning(
            "scoring_dimension_failed", dimension="demand_result", arxiv_id=arxiv_id, error=str(e)
        )
        return {"demand_result": None}
