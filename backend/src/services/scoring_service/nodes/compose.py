"""compose_and_persist node: assemble the four dimension results and persist.

Fan-in join. Writes one `paper_scores` row (NULL for any soft-failed dimension) plus its
`score_evidence` rows via `ScoringRepository.upsert_score` (idempotent on rubric version).
The Celery task owns the commit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.schemas.scoring_state import DimensionScore, PaperScoreState
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.services.scoring_service.context import ScoringContext

log = get_logger(__name__)

# Column name per dimension, and which dimensions are LLM-judged (for `details.model`).
_DIMENSION_COLUMNS: dict[str, str] = {
    "method_clarity": "method_clarity_score",
    "resource_feasibility": "resource_feasibility_score",
    "data_availability": "data_availability_score",
    "demand": "demand_score",
}
_LLM_DIMENSIONS = frozenset({"method_clarity", "resource_feasibility"})


async def compose_and_persist_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context: ScoringContext = config["configurable"]["context"]

    results: dict[str, DimensionScore | None] = {
        "method_clarity": state.get("method_clarity_result"),
        "resource_feasibility": state.get("resource_feasibility_result"),
        "data_availability": state.get("data_availability_result"),
        "demand": state.get("demand_result"),
    }

    scores: dict[str, int | None] = {
        column: (results[dim].score if results[dim] else None)
        for dim, column in _DIMENSION_COLUMNS.items()
    }

    details: dict[str, dict] = {}
    evidence: list[dict] = []
    for dim, result in results.items():
        if result is None:
            continue
        details[dim] = {
            "reasoning": result.reasoning,
            "model": context.strong_model if dim in _LLM_DIMENSIONS else None,
        }
        for span in result.evidence:
            evidence.append(
                {"dimension": dim, "kind": span.kind, "text": span.text, "source": span.source}
            )

    await context.scoring_repository.upsert_score(
        paper_id=state["paper_id"],
        rubric_version=state["rubric_version"],
        scores=scores,
        details=details,
        evidence=evidence,
    )

    scored = [dim for dim, r in results.items() if r is not None]
    log.info(
        "scoring_composed",
        arxiv_id=state["arxiv_id"],
        paper_id=state["paper_id"],
        scored_dimensions=scored,
    )
    return {}
