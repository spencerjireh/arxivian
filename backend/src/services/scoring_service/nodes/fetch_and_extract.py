"""fetch_and_extract node: ensure full text, then build the Jev request inputs.

Two kinds of input feed the dimension nodes:

- `extracted_spans`: per-kind SEMANTIC retrieval scoped to the paper's own chunks
  (pseudocode / compute / dataset probes) plus `code_mentions` found by regex over the
  raw text. These double as the stored evidence spans.
- `sections`: abstract / method / experiments / appendix headings split from
  `paper.raw_text` (`utils.section_splitter`), the targeted state Jev judges over.

Hard-fails (raises) when there is no usable full text -- a paper cannot be scored from
nothing, so Celery should retry rather than persist an empty row. Commits after ingest so
a later rate-limit abort in a dimension node does not roll back the ingested paper.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.exceptions import ScoringError
from src.services.scoring_service.state import PaperScoreState
from src.utils.logger import get_logger
from src.utils.section_splitter import code_mentions, extract_sections

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

    # Ingest ran inside this session; make it durable before the Jev calls so a
    # TypeSafe rate-limit abort (re-raised to the task for retry) keeps the full text.
    await context.db_session.commit()

    extracted_spans: dict[str, list[str]] = {}
    for kind, probe in DIMENSION_PROBES.items():
        results = await context.search_service.retrieve_within_paper(
            query=probe, paper_id=paper_id, top_k=SPANS_PER_DIMENSION
        )
        extracted_spans[kind] = [r.chunk_text for r in results]

    raw_text = paper.raw_text or ""
    if not raw_text:
        log.warning("scoring_raw_text_missing", arxiv_id=arxiv_id, paper_id=paper_id)
    extracted_spans["code_mentions"] = code_mentions(raw_text)
    sections = extract_sections(raw_text, abstract=paper.abstract or "")

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
        section_chars={k: len(v) for k, v in sections.items()},
    )
    return {
        "paper_id": paper_id,
        "paper_meta": paper_meta,
        "extracted_spans": extracted_spans,
        "sections": sections,
    }
