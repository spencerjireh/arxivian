"""The four dimension nodes (rubric v2).

Three dimensions are Jev judgments over targeted state (method clarity, resource
feasibility, data availability); one is a Semantic Scholar lookup (demand). Each Jev
node makes exactly one `system_one` request and hands the normalized answers to
`judgments.py` to build its `DimensionScore`.

Failure policy: a TypeSafe rate-limit or connection error is RE-RAISED -- it aborts the
graph so `score_paper_task` can retry the whole paper later with the server's
`retry_after`. Everything else SOFT-FAILS: the node returns its result key as `None`, the
column persists NULL, and the rest of the paper still scores.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from langchain_core.runnables import RunnableConfig

from src.clients.typesafe_client import Question, SystemOneResult
from src.exceptions import TypeSafeConnectionError, TypeSafeRateLimitError
from src.schemas.scoring_state import (
    DEMAND_BAND_TO_SCORE,
    EvidenceKind,
    EvidenceSpan,
    PaperAttributes,
    PaperScoreState,
)
from src.services.scoring_service import questions as q
from src.services.scoring_service.judgments import (
    choice_judgment,
    combine_data_availability,
    combine_method_clarity,
    combine_resource_feasibility,
    demand_from_band,
    noul_judgment,
)
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.services.scoring_service.context import ScoringContext

log = get_logger(__name__)

__all__ = [
    "DEMAND_BAND_TO_SCORE",
    "score_method_clarity_node",
    "score_resource_feasibility_node",
    "score_data_availability_node",
    "score_demand_node",
]

# Evidence spans kept per kind (the same spans are sent as state, truncated for storage).
EVIDENCE_SPANS_PER_KIND = 3
EVIDENCE_SPAN_CHARS = 600


def _evidence(
    spans: list[str], kind: EvidenceKind, source: str = "retrieved"
) -> list[EvidenceSpan]:
    return [
        EvidenceSpan(text=span[:EVIDENCE_SPAN_CHARS], kind=kind, source=source)
        for span in spans[:EVIDENCE_SPANS_PER_KIND]
    ]


def _usage(result: SystemOneResult) -> dict[str, Any]:
    return {"model": result.model, "input_tokens": result.input_tokens}


async def _ask(
    context: ScoringContext,
    state: PaperScoreState,
    payload: dict[str, Any],
    questions: Mapping[str, Question],
    *,
    request_name: str,
) -> SystemOneResult:
    """One Jev request. Transient errors propagate; see the module docstring."""
    try:
        return await context.typesafe_client.ask(payload, questions, request_name=request_name)
    except (TypeSafeRateLimitError, TypeSafeConnectionError):
        log.warning(
            "scoring_dimension_transient_error", request=request_name, arxiv_id=state["arxiv_id"]
        )
        raise


def _soft_fail(result_keys: tuple[str, ...], state: PaperScoreState, error: Exception) -> dict:
    log.warning(
        "scoring_dimension_failed",
        dimension=result_keys[0],
        arxiv_id=state["arxiv_id"],
        error=str(error),
    )
    return {key: None for key in result_keys}


# --- Method clarity + product attributes ----------------------------------------------


async def score_method_clarity_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context: ScoringContext = config["configurable"]["context"]
    keys = ("method_clarity_result", "attributes_result", "method_clarity_usage")
    try:
        spans = state["extracted_spans"]
        sections = state["sections"]
        payload = {
            "abstract": sections.get("abstract", ""),
            "method": sections.get("method", ""),
            "experiments": sections.get("experiments", ""),
            "pseudocode_spans": spans.get("pseudocode") or [],
            "code_mentions": spans.get("code_mentions") or [],
        }
        questions: dict[str, Question] = {**q.METHOD_CLARITY_QUESTIONS, **q.ATTRIBUTE_QUESTIONS}
        result = await _ask(context, state, payload, questions, request_name="method_clarity")

        evidence = _evidence(spans.get("pseudocode") or [], "pseudocode")
        dimension = combine_method_clarity(result.nouls, q.METHOD_CLARITY_CRITERIA, evidence)
        attributes = PaperAttributes(
            code_released=noul_judgment("code_released", result.nouls["code_released"]),
            task_type=choice_judgment("task_type", result.choices["task_type"]),
            model_family=choice_judgment("model_family", result.choices["model_family"]),
        )
        return {
            "method_clarity_result": dimension,
            "attributes_result": attributes,
            "method_clarity_usage": _usage(result),
        }
    except (TypeSafeRateLimitError, TypeSafeConnectionError):
        raise
    except Exception as e:
        return _soft_fail(keys, state, e)


# --- Resource feasibility -------------------------------------------------------------


async def score_resource_feasibility_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context: ScoringContext = config["configurable"]["context"]
    keys = ("resource_feasibility_result", "resource_feasibility_usage")
    try:
        spans = state["extracted_spans"]
        sections = state["sections"]
        payload = {
            "abstract": sections.get("abstract", ""),
            "experiments": sections.get("experiments", ""),
            "compute_spans": spans.get("compute") or [],
        }
        questions: dict[str, Question] = {
            "compute_tier": q.COMPUTE_TIER,
            **q.FEASIBILITY_AUX_QUESTIONS,
        }
        result = await _ask(context, state, payload, questions, request_name="resource_feasibility")

        evidence = _evidence(spans.get("compute") or [], "compute")
        aux = {k: result.nouls[k] for k in q.FEASIBILITY_AUX_QUESTIONS}
        dimension = combine_resource_feasibility(result.scores["compute_tier"], aux, evidence)
        return {
            "resource_feasibility_result": dimension,
            "resource_feasibility_usage": _usage(result),
        }
    except (TypeSafeRateLimitError, TypeSafeConnectionError):
        raise
    except Exception as e:
        return _soft_fail(keys, state, e)


# --- Data availability gate -----------------------------------------------------------


async def score_data_availability_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context: ScoringContext = config["configurable"]["context"]
    keys = ("data_availability_result", "data_availability_usage")
    try:
        spans = state["extracted_spans"]
        sections = state["sections"]
        payload = {
            "abstract": sections.get("abstract", ""),
            "dataset_spans": spans.get("dataset") or [],
        }
        result = await _ask(
            context,
            state,
            payload,
            {"data_access": q.DATA_ACCESS},
            request_name="data_availability",
        )

        evidence = _evidence(spans.get("dataset") or [], "dataset")
        dimension = combine_data_availability(
            result.choices["data_access"], q.GATE_PASS_OPTIONS, evidence
        )
        return {
            "data_availability_result": dimension,
            "data_availability_usage": _usage(result),
        }
    except (TypeSafeRateLimitError, TypeSafeConnectionError):
        raise
    except Exception as e:
        return _soft_fail(keys, state, e)


# --- Demand (Semantic Scholar, no Jev) ------------------------------------------------


async def score_demand_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context: ScoringContext = config["configurable"]["context"]
    arxiv_id = state["arxiv_id"]
    try:
        metrics = await context.semantic_scholar_client.get_citation_metrics(arxiv_id)
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
            f"{metrics.demand_band} -> demand {DEMAND_BAND_TO_SCORE[metrics.demand_band]}."
        )
        return {"demand_result": demand_from_band(metrics.demand_band, evidence, reasoning)}
    except Exception as e:
        return _soft_fail(("demand_result",), state, e)
