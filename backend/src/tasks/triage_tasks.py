"""Stage 1 cheap triage -- the scoring pipeline's entry point.

Weekly Beat-triggered batch task. Crawls new arXiv submissions for the configured
categories (title + abstract only, NO PDF), runs a single coarse keep/drop classification
over batched abstracts on the cheap default model, and enqueues one Stage 2
`score_paper_task` per survivor. The bulk (~70-80%) is dropped before any full-text cost.

Mirrors `scheduled_tasks.py::daily_ingest_task`: a fan-out driver (no bind/retry) with an
inner `_run()` coroutine dispatched via `run_async`, deterministic task IDs, and staggered
enqueues. Reject audit is log-only (no triage table); survivors advance by `arxiv_id`, since
Stage 2 ingests the full text and creates the paper row itself.

See `ARX-55` -> "Stage 1 -- Cheap Triage".
"""

import asyncio
import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded

from src.celery_app import celery_app
from src.config import get_settings
from src.factories import get_arxiv_client, get_llm_client
from src.services.scoring_service.triage import (
    TriageBatchResult,
    TriageResult,
    get_triage_batch_prompt,
    normalize_arxiv_id,
)
from src.tasks.runtime import run_async
from src.tasks.score_tasks import score_paper_task
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
    key = f"{datetime.now(UTC).date().isoformat()}:{category}:{arxiv_id}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def _chunked(items: Sequence[Any], size: int) -> list[Sequence[Any]]:
    """Split a sequence into consecutive chunks of at most `size`."""
    return [items[i : i + size] for i in range(0, len(items), size)]


_TRIAGE_TIMEOUT = get_settings().triage_task_timeout


@celery_app.task(
    name="src.tasks.triage_tasks.triage_new_papers_task",
    # Overrides the global task_time_limit for this one task. soft fires a catchable
    # exception first so a slow run still enqueues what it has; hard is the backstop.
    soft_time_limit=_TRIAGE_TIMEOUT,
    time_limit=_TRIAGE_TIMEOUT + 60,
)
def triage_new_papers_task() -> dict[str, Any]:
    """Crawl, triage, and enqueue survivors for deep scoring.

    Returns:
        Summary dict with crawl/survivor/reject counts and the enqueued survivors.
    """
    log.info("triage_started")

    async def _run() -> dict[str, Any]:
        settings = get_settings()
        arxiv_client = get_arxiv_client()
        llm_client = get_llm_client()  # cheap default model (no override)

        today = datetime.now(UTC).date()
        start_date = (today - timedelta(days=settings.triage_lookback_days)).isoformat()
        end_date = today.isoformat()

        # Crawl each category, deduping globally by arxiv_id (first-seen category wins, so
        # cross-listed papers are triaged and enqueued once).
        candidates: dict[str, dict[str, Any]] = {}
        for i, category in enumerate(settings.triage_categories):
            if i > 0:
                # Pace the crawl so back-to-back category scans do not trip arXiv's
                # rate limit (ARX-16); the arxiv.Client keeps its own per-page delay.
                await asyncio.sleep(settings.arxiv_crawl_pause_seconds)
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

        # Classify in batches, concurrently under a semaphore. Sequentially this was ~33s
        # per batch, so 4x100 candidates ran ~660s past the 600s limit and the SIGKILL threw
        # the entire run away (ARX-67). A failed batch is logged and skipped (those papers
        # get no verdict this run and are neither enqueued nor counted as rejected).
        verdicts: dict[str, TriageResult] = {}
        batches = _chunked(crawled, TRIAGE_BATCH_SIZE)
        semaphore = asyncio.Semaphore(settings.triage_batch_concurrency)

        async def classify(batch: Sequence[Any]) -> None:
            """Classify one batch and merge its verdicts into `verdicts` immediately.

            Writing into the shared dict as each batch lands, rather than returning results
            for the caller to collect, is deliberate: `asyncio.gather` discards the results
            of completed coroutines when it propagates an exception, so on a soft timeout a
            collect-at-the-end version would still throw away every finished batch.
            """
            system, user = get_triage_batch_prompt(batch)
            async with semaphore:
                try:
                    result = await llm_client.generate_structured(
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        response_format=TriageBatchResult,
                    )
                except SoftTimeLimitExceeded:
                    # Must not be swallowed by the handler below: it has to unwind so the
                    # remaining batches stop instead of running on past the hard limit.
                    raise
                except Exception as exc:
                    log.error("triage_batch_failed", error=str(exc), batch_size=len(batch))
                    return
            for verdict in result.results:
                verdicts[normalize_arxiv_id(verdict.arxiv_id)] = verdict

        # The soft limit is raised into whichever batch is in flight. Catching it here turns
        # a wasted run into a degraded one: everything classified so far is still enqueued.
        timed_out = False
        try:
            await asyncio.gather(*(classify(batch) for batch in batches))
        except SoftTimeLimitExceeded:
            log.error(
                "triage_soft_time_limit",
                batches=len(batches),
                verdicts=len(verdicts),
                timeout=_TRIAGE_TIMEOUT,
            )
            timed_out = True

        log.info(
            "triage_classified",
            batches=len(batches),
            verdicts=len(verdicts),
            concurrency=settings.triage_batch_concurrency,
            timed_out=timed_out,
        )

        # Select survivors, then enqueue. Separating the two passes is what lets the cap
        # keep the *best* candidates rather than whichever happen to come first out of the
        # crawl dedupe, which is insertion-ordered by category.
        keepers: list[tuple[int, dict[str, Any]]] = []
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
            keepers.append((verdict.rough_implementability, candidate))

        keepers.sort(key=lambda pair: pair[0], reverse=True)
        capped = max(0, len(keepers) - settings.triage_max_survivors)
        if capped:
            log.warning(
                "triage_survivors_capped",
                kept=settings.triage_max_survivors,
                dropped=capped,
                cap=settings.triage_max_survivors,
            )
        keepers = keepers[: settings.triage_max_survivors]

        enqueued: list[dict[str, str]] = []
        for _, candidate in keepers:
            arxiv_id = candidate["arxiv_id"]
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
            "capped": capped,
            "timed_out": timed_out,
            "enqueued": enqueued,
        }

    result = run_async(_run())
    log.info(
        "triage_completed",
        crawled=result["crawled"],
        survivors=result["survivors"],
        rejected=result["rejected"],
        capped=result["capped"],
        timed_out=result["timed_out"],
    )
    return result
