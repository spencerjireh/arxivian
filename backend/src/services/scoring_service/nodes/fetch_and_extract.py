"""fetch_and_extract node: ensure full text, then build extracted_spans via retrieval.

Extraction is per-dimension SEMANTIC retrieval scoped to the paper's own chunks (not a
keyword scan): extraction recall directly bounds the two LLM judgments, and Stage 2 runs on
survivors only, so recall matters more than shaving a call. Hard-fails (raises) when there
is no usable full text -- a paper cannot be scored from nothing, so Celery should retry
rather than persist an empty row.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.exceptions import ScoringError
from src.schemas.scoring_state import PaperScoreState
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.services.scoring_service.context import ScoringContext

log = get_logger(__name__)

# One retrieval probe per evidence kind. Keys match what the dimension prompts / gate read.
DIMENSION_PROBES: dict[str, str] = {
    "pseudocode": (
        "algorithm pseudocode method steps training procedure hyperparameters "
        "learning rate architecture model design"
    ),
    "compute": (
        "GPU TPU hardware training compute GPU-hours number of parameters model size "
        "batch size epochs training time"
    ),
    "dataset": (
        "dataset benchmark corpus training data evaluation data data source data collection"
    ),
}

# Chunks retrieved per dimension probe.
SPANS_PER_DIMENSION = 5


async def fetch_and_extract_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context: ScoringContext = config["configurable"]["context"]
    arxiv_id = state["arxiv_id"]

    # Idempotent: ingests full text + chunks if absent, no-ops if already present.
    await context.ingest_service.ingest_by_ids([arxiv_id])

    paper = await context.paper_repository.get_by_arxiv_id(arxiv_id)
    if paper is None or not paper.pdf_processed:
        raise ScoringError(f"No usable full text for {arxiv_id} (paper missing or not processed)")

    paper_id = str(paper.id)

    extracted_spans: dict[str, list[str]] = {}
    for kind, probe in DIMENSION_PROBES.items():
        results = await context.search_service.retrieve_within_paper(
            query=probe, paper_id=paper_id, top_k=SPANS_PER_DIMENSION
        )
        extracted_spans[kind] = [r.chunk_text for r in results]

    paper_meta = {
        "title": paper.title,
        "arxiv_id": arxiv_id,
        "abstract": paper.abstract or "",
    }

    log.info(
        "scoring_fetch_and_extract",
        arxiv_id=arxiv_id,
        paper_id=paper_id,
        spans={k: len(v) for k, v in extracted_spans.items()},
    )
    return {
        "paper_id": paper_id,
        "paper_meta": paper_meta,
        "extracted_spans": extracted_spans,
    }
