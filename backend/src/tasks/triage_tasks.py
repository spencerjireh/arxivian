"""Stage 1 cheap triage -- the scoring pipeline's entry point.

Weekly Beat-triggered batch task. Crawls new arXiv submissions for the configured
categories (title + abstract only, NO PDF), runs a single coarse keep/drop classification
over batched abstracts on the cheap default model, and enqueues one Stage 2
`score_paper_task` per survivor. The bulk (~70-80%) is dropped before any full-text cost.

Mirrors `scheduled_tasks.py::daily_ingest_task`: a fan-out driver (no bind/retry) with an
inner `_run()` coroutine dispatched via `run_async`, deterministic task IDs, and staggered
enqueues. Reject audit is log-only (no triage table); survivors advance by `arxiv_id`, since
Stage 2 ingests the full text and creates the paper row itself.

See `docs/design/scoring-pipeline.md` -> "Stage 1 -- Cheap Triage".
"""

import hashlib
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from src.celery_app import celery_app
from src.factories.client_factories import get_arxiv_client, get_llm_client
from src.schemas.triage import TriageBatchResult, TriageResult
from src.services.scoring_service.triage_prompt import get_triage_batch_prompt
from src.tasks.score_tasks import score_paper_task
from src.tasks.utils import run_async
from src.utils.logger import get_logger

log = get_logger(__name__)

# Abstracts per classification call. Batching cuts request count against provider rate limits.
TRIAGE_BATCH_SIZE = 20
# Seconds between successive Stage 2 enqueues, to spread external-API load (Semantic Scholar).
STAGGER_SECONDS = 5


def _triage_task_id(category: str, arxiv_id: str) -> str:
    """Deterministic Stage 2 task ID, so weekly re-runs dedupe the same survivor.

    Keyed on date + category + arXiv ID (mirrors `scheduled_tasks._deterministic_task_id`).
    """
    key = f"{datetime.now(timezone.utc).date().isoformat()}:{category}:{arxiv_id}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def _chunked(items: Sequence[Any], size: int) -> list[Sequence[Any]]:
    """Split a sequence into consecutive chunks of at most `size`."""
    return [items[i : i + size] for i in range(0, len(items), size)]


@celery_app.task(name="src.tasks.triage_tasks.triage_new_papers_task")
def triage_new_papers_task() -> dict[str, Any]:
    """Crawl, triage, and enqueue survivors for deep scoring.

    Returns:
        Summary dict with crawl/survivor/reject counts and the enqueued survivors.
    """
    log.info("triage_started")

    async def _run() -> dict[str, Any]:
        from src.config import get_settings

        settings = get_settings()
        arxiv_client = get_arxiv_client()
        llm_client = get_llm_client()  # cheap default model (no override)

        today = datetime.now(timezone.utc).date()
        start_date = (today - timedelta(days=settings.triage_lookback_days)).isoformat()
        end_date = today.isoformat()

        # Crawl each category, deduping globally by arxiv_id (first-seen category wins, so
        # cross-listed papers are triaged and enqueued once).
        candidates: dict[str, dict[str, Any]] = {}
        for category in settings.triage_categories:
            papers = await arxiv_client.search_papers(
                query="",
                categories=[category],
                max_results=settings.triage_max_per_category,
                start_date=start_date,
                end_date=end_date,
            )
            for paper in papers:
                if paper.arxiv_id in candidates:
                    continue
                candidates[paper.arxiv_id] = {
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "abstract": paper.abstract,
                    "category": category,
                }

        crawled = list(candidates.values())
        log.info(
            "triage_crawl_complete", crawled=len(crawled), categories=settings.triage_categories
        )

        # Classify in batches. A failed batch is logged and skipped (those papers get no
        # verdict this run and are neither enqueued nor counted as rejected).
        verdicts: dict[str, TriageResult] = {}
        for batch in _chunked(crawled, TRIAGE_BATCH_SIZE):
            system, user = get_triage_batch_prompt(batch)
            try:
                result = await llm_client.generate_structured(
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format=TriageBatchResult,
                )
            except Exception as exc:
                log.error("triage_batch_failed", error=str(exc), batch_size=len(batch))
                continue
            for verdict in result.results:
                verdicts[verdict.arxiv_id] = verdict

        # Enqueue survivors; log rejects.
        enqueued: list[dict[str, str]] = []
        rejected = 0
        for candidate in candidates.values():
            arxiv_id = candidate["arxiv_id"]
            verdict = verdicts.get(arxiv_id)
            if verdict is None:
                log.warning("triage_no_verdict", arxiv_id=arxiv_id)
                continue
            if not verdict.keep:
                rejected += 1
                log.info(
                    "triage_paper_rejected",
                    arxiv_id=arxiv_id,
                    paper_class=verdict.paper_class,
                    reasoning=verdict.reasoning,
                )
                continue

            det_id = _triage_task_id(candidate["category"], arxiv_id)
            score_paper_task.apply_async(
                kwargs={"arxiv_id": arxiv_id},
                countdown=len(enqueued) * STAGGER_SECONDS,
                task_id=det_id,
            )
            enqueued.append(
                {"arxiv_id": arxiv_id, "task_id": det_id, "category": candidate["category"]}
            )
            log.info("triage_paper_kept", arxiv_id=arxiv_id, task_id=det_id)

        return {
            "status": "completed",
            "categories": settings.triage_categories,
            "crawled": len(crawled),
            "survivors": len(enqueued),
            "rejected": rejected,
            "enqueued": enqueued,
        }

    result = run_async(_run())
    log.info(
        "triage_completed",
        crawled=result["crawled"],
        survivors=result["survivors"],
        rejected=result["rejected"],
    )
    return result
