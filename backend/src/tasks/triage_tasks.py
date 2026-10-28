"""Stage 1 cheap triage -- the scoring pipeline's entry point.

Weekly Beat-triggered batch task. Crawls new arXiv submissions for the configured
categories (title + abstract only, NO PDF), runs a single coarse keep/drop classification
over batched abstracts on the cheap default model, and enqueues one Stage 2
`score_paper_task` per survivor.

The prompt is recall-biased on purpose, so triage drops only the obvious non-artifacts --
surveys, position papers, theory, benchmarks -- observed at **~7%**, not the ~70-80% this
docstring claimed until ARX-70. What actually bounds Stage 2 volume, and therefore the feed,
is `triage_max_survivors`.

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


def _apply_survivor_cap(
    keepers: list[tuple[int, dict[str, Any]]], cap: int
) -> list[tuple[int, dict[str, Any]]]:
    """Trim to `cap`, but never split a group of papers sharing a `rough_implementability`.

    A plain `keepers[:cap]` looks like ranking and is not. The sort key is a coarse LLM guess
    with very little resolution -- measured on a 1588-paper crawl it took only 38 distinct
    values across 1363 keepers, with 72% of them on just six round numbers -- so the cut
    almost always lands inside a large tie group, where inclusion is decided by crawl order.
    At the cap of 150 that ran in production, 83 papers tied on 72: nine were enqueued and 74
    were dropped on nothing but their position in the list.

    Taking the whole straddling group removes that arbitrariness. It makes the cap a floor
    rather than a ceiling, which is the right trade: Stage 1 is cents, Stage 2 is ~$1.50 per
    1000 papers, and the feed ranks by the Stage 2 composite anyway -- the cap only decides
    who gets scored. Ordering within a tie is still arbitrary, but it no longer decides
    whether a paper is seen at all.

    Returns every keeper when `cap` is non-positive, matching the previous slice behaviour.
    """
    if cap <= 0 or len(keepers) <= cap:
        return keepers
    boundary_score = keepers[cap - 1][0]
    # keepers is sorted descending, so the tie group runs contiguously past the cut.
    end = cap
    while end < len(keepers) and keepers[end][0] == boundary_score:
        end += 1
    return keepers[:end]


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
        failed_categories: list[str] = []
        for i, category in enumerate(settings.triage_categories):
            if i > 0:
                # Pace the crawl so back-to-back category scans do not trip arXiv's
                # rate limit (ARX-16); the arxiv.Client keeps its own per-page delay.
                await asyncio.sleep(settings.arxiv_crawl_pause_seconds)
            try:
                papers = await arxiv_client.search_papers(
                    query="",
                    categories=[category],
                    max_results=settings.triage_max_per_category,
                    start_date=start_date,
                    end_date=end_date,
                )
            except SoftTimeLimitExceeded:
                # Must unwind: the run is out of time and the phases below need what is left
                # of the budget more than another category does.
                raise
            except Exception as exc:
                # One category must not take the run with it. On 2026-10-26 arXiv answered
                # 429 on page 5 of cs.LG -- the first of four -- and because this call was
                # unguarded the exception left `_run` and the whole week went unscored, with
                # cs.CL, cs.CV and cs.AI never attempted. Three categories out of four is a
                # thinner feed; nothing at all is an outage.
                failed_categories.append(category)
                log.error("triage_category_failed", category=category, error=str(exc))
                continue
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
            "triage_crawl_complete",
            crawled=len(crawled),
            categories=settings.triage_categories,
            failed_categories=failed_categories,
        )
        if not crawled:
            # Every category failed. Returning here rather than running the phases below
            # keeps the failure legible: an empty verdict set downstream is indistinguishable
            # from "nothing qualified", which is how ARX-67 stayed hidden for a week.
            log.error("triage_crawl_empty", failed_categories=failed_categories)
            return {
                "status": "failed",
                "reason": "every category failed to crawl",
                "categories": settings.triage_categories,
                "failed_categories": failed_categories,
                "crawled": 0,
                "survivors": 0,
                "rejected": 0,
                "capped": 0,
                "no_verdict": 0,
                "timed_out": False,
            }

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

        # The model sometimes omits ids from a batch response: 20 of 366 in the first
        # production run. Dropping those silently contradicts the prompt's own economics
        # ("a false keep is far cheaper than a false drop"), so give them one more pass
        # (ARX-70). Skipped after a soft timeout -- more calls then would reach the hard
        # limit and lose the whole run, which is the ARX-67 failure.
        missing = [c for c in candidates.values() if c["arxiv_id"] not in verdicts]
        if missing and not timed_out:
            try:
                await asyncio.gather(
                    *(classify(batch) for batch in _chunked(missing, TRIAGE_BATCH_SIZE))
                )
            except SoftTimeLimitExceeded:
                log.error("triage_soft_time_limit", phase="reclassify", verdicts=len(verdicts))
                timed_out = True
            recovered = sum(1 for c in missing if c["arxiv_id"] in verdicts)
            log.info("triage_reclassified", missing=len(missing), recovered=recovered)

        no_verdict = sum(1 for c in candidates.values() if c["arxiv_id"] not in verdicts)

        log.info(
            "triage_classified",
            batches=len(batches),
            verdicts=len(verdicts),
            no_verdict=no_verdict,
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
        all_keepers = keepers
        keepers = _apply_survivor_cap(keepers, settings.triage_max_survivors)
        capped = max(0, len(all_keepers) - len(keepers))
        if capped or len(keepers) > settings.triage_max_survivors:
            log.warning(
                "triage_survivors_capped",
                kept=len(keepers),
                dropped=capped,
                cap=settings.triage_max_survivors,
                tie_extra=len(keepers) - settings.triage_max_survivors,
                boundary_score=keepers[-1][0] if keepers else None,
            )

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
            "failed_categories": failed_categories,
            "crawled": len(crawled),
            "survivors": len(enqueued),
            "rejected": rejected,
            "capped": capped,
            "no_verdict": no_verdict,
            "timed_out": timed_out,
            "enqueued": enqueued,
        }

    # +30s so the Celery soft limit (which the task catches, preserving partial work) always
    # fires before this backstop. Ordering: soft _TRIAGE_TIMEOUT -> this -> hard +60.
    result = run_async(_run(), timeout=_TRIAGE_TIMEOUT + 30)
    log.info(
        "triage_completed",
        status=result["status"],
        crawled=result["crawled"],
        survivors=result["survivors"],
        rejected=result["rejected"],
        capped=result["capped"],
        no_verdict=result["no_verdict"],
        timed_out=result["timed_out"],
        # Non-empty means the crawl was partial: the feed covers fewer categories than
        # configured, which is the difference between a thin week and a correct one.
        failed_categories=result.get("failed_categories", []),
    )
    return result
