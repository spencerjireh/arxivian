"""compose_and_persist node: assemble the dimension results and persist (rubric v2).

Fan-in join. Writes one `paper_scores` row: the full per-dimension distributions in
`dimensions` (JSONB), the product attributes, the Jev model/usage, and the four derived
0-100 columns (NULL for any soft-failed dimension) plus `score_evidence` rows, via
`ScoringRepository.upsert_score` (idempotent on rubric version). The Celery task owns
the commit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.services.scoring_service.state import DimensionScore, PaperScoreState
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.services.scoring_service.context import ScoringContext

log = get_logger(__name__)

# Derived-score column per dimension.
_DIMENSION_COLUMNS: dict[str, str] = {
    "method_clarity": "method_clarity_score",
    "resource_feasibility": "resource_feasibility_score",
    "data_availability": "data_availability_score",
    "demand": "demand_score",
}
_USAGE_KEYS = ("method_clarity_usage", "resource_feasibility_usage", "data_availability_usage")


async def compose_and_persist_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context: ScoringContext = config["configurable"]["context"]

    results: dict[str, DimensionScore | None] = {
        "method_clarity": state.get("method_clarity_result"),
        "resource_feasibility": state.get("resource_feasibility_result"),
        "data_availability": state.get("data_availability_result"),
        "demand": state.get("demand_result"),
    }

    scores: dict[str, int | None] = {}
    for dim, column in _DIMENSION_COLUMNS.items():
        result = results[dim]
        scores[column] = result.derived_score() if result is not None else None

    dimensions: dict[str, dict] = {}
    evidence: list[dict] = []
    for dim, result in results.items():
        if result is None:
            continue
        # mode="json" turns the int probability keys into strings for JSONB.
        dimensions[dim] = result.model_dump(mode="json")
        evidence.extend(
            {"dimension": dim, "kind": span.kind, "text": span.text, "source": span.source}
            for span in result.evidence
        )

    attributes_result = state.get("attributes_result")
    attributes = attributes_result.model_dump(mode="json") if attributes_result else None
    evidence.extend(
        {"dimension": "code_released", "kind": "code", "text": mention, "source": "raw_text"}
        for mention in (state.get("extracted_spans") or {}).get("code_mentions") or []
    )

    usages = [u for u in (state.get(key) for key in _USAGE_KEYS) if u]
    model = next((u["model"] for u in usages if u.get("model")), None)
    token_counts = [u["input_tokens"] for u in usages if u.get("input_tokens") is not None]
    input_tokens = sum(token_counts) if token_counts else None

    await context.scoring_repository.upsert_score(
        paper_id=state["paper_id"],
        rubric_version=state["rubric_version"],
        scores=scores,
        dimensions=dimensions,
        evidence=evidence,
        attributes=attributes,
        model=model,
        input_tokens=input_tokens,
    )

    scored = [dim for dim, r in results.items() if r is not None]
    log.info(
        "scoring_composed",
        arxiv_id=state["arxiv_id"],
        paper_id=state["paper_id"],
        scored_dimensions=scored,
        model=model,
        input_tokens=input_tokens,
    )
    return {}
