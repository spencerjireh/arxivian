"""Dump one weekly triage crawl with its verdicts, for offline selection analysis.

Stage 1 persists nothing. `triage_tasks.py` writes no database row for any candidate: a
rejected paper leaves only a log line, a capped paper leaves only an aggregate count, and
even a survivor's verdict is dropped once Stage 2 re-fetches the paper itself. So the
question "is the feed selecting the right papers" cannot be answered from stored data --
the sample has to be generated fresh, which is what this script does.

It mirrors the production path rather than reimplementing it: the same
`ArxivClient.search_papers` arguments as `triage_tasks.py`, the same
`get_triage_batch_prompt` and `TriageBatchResult`, the same batch size and concurrency, and
the same `normalize_arxiv_id` on both sides of the join. What it does NOT do is enqueue
anything -- no Stage 2 task is created and nothing is written to the database.

Verdicts are not expected to reproduce a past week exactly; the model is not deterministic.
The point is a representative sample of how triage and its sort key behave, not a replay.

Usage, from the repo root with the dev stack up:

    docker compose --profile dev exec -T app \\
        uv run python -m scripts.dump_triage_candidates --out /tmp/candidates.jsonl

See ARX-70 for the crawl-coverage instrumentation this reads alongside.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.factories import get_arxiv_client, get_llm_client
from src.services.scoring_service.triage import (
    TriageBatchResult,
    TriageResult,
    get_triage_batch_prompt,
    normalize_arxiv_id,
)

# Mirrors tasks/triage_tasks.py; keep them in step or the sample stops describing production.
TRIAGE_BATCH_SIZE = 20


def _progress(message: str) -> None:
    """Progress goes to stderr so stdout stays free for redirection, as in export_openapi."""
    sys.stderr.write(message + "\n")


def _chunked(items: Sequence[Any], size: int) -> list[Sequence[Any]]:
    """Split a sequence into consecutive chunks of at most `size`."""
    return [items[i : i + size] for i in range(0, len(items), size)]


async def _crawl(
    categories: list[str], max_per_category: int, lookback_days: int, pause_seconds: int
) -> dict[str, dict[str, Any]]:
    """Crawl each category, deduping globally by arxiv_id (first-seen category wins)."""
    arxiv_client = get_arxiv_client()
    today = datetime.now(UTC).date()
    start_date = (today - timedelta(days=lookback_days)).isoformat()
    end_date = today.isoformat()

    candidates: dict[str, dict[str, Any]] = {}
    for i, category in enumerate(categories):
        if i > 0:
            # Same pacing as production: back-to-back scans trip arXiv's rate limit (ARX-16).
            await asyncio.sleep(pause_seconds)
        papers = await arxiv_client.search_papers(
            query="",
            categories=[category],
            max_results=max_per_category,
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
        _progress(f"  {category}: {len(papers)} returned, {len(candidates)} unique so far")
    return candidates


async def _classify(crawled: list[dict[str, Any]], concurrency: int) -> dict[str, TriageResult]:
    """Classify every candidate, merging verdicts as each batch lands."""
    llm_client = get_llm_client()
    verdicts: dict[str, TriageResult] = {}
    semaphore = asyncio.Semaphore(concurrency)
    batches = _chunked(crawled, TRIAGE_BATCH_SIZE)
    done = 0

    async def classify_batch(batch: Sequence[Any]) -> None:
        nonlocal done
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
            except Exception as exc:  # a dropped batch is reported and skipped, not fatal
                _progress(f"  batch failed ({len(batch)} papers): {exc}")
                return
        for verdict in result.results:
            verdicts[normalize_arxiv_id(verdict.arxiv_id)] = verdict
        done += 1
        if done % 10 == 0:
            _progress(f"  {done}/{len(batches)} batches")

    await asyncio.gather(*(classify_batch(batch) for batch in batches))
    return verdicts


def _rows(
    candidates: dict[str, dict[str, Any]], verdicts: dict[str, TriageResult], cap: int
) -> list[dict[str, Any]]:
    """Join candidates to verdicts and derive each one's outcome under `cap`.

    `outcome` reproduces what production would have done: rejected by triage, kept but cut
    by the survivor cap, or enqueued for Stage 2. `no_verdict` means the model omitted the
    id from its batch response, which production re-batches once (ARX-70); here it is left
    visible rather than retried, so the rate stays measurable.
    """
    keepers = sorted(
        (
            (v.rough_implementability, aid)
            for aid, v in verdicts.items()
            if v.keep and aid in candidates
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    survived = {aid for _, aid in keepers[:cap]}

    rows: list[dict[str, Any]] = []
    for arxiv_id, candidate in candidates.items():
        verdict = verdicts.get(arxiv_id)
        if verdict is None:
            outcome = "no_verdict"
        elif not verdict.keep:
            outcome = "rejected"
        elif arxiv_id in survived:
            outcome = "survived"
        else:
            outcome = "capped"
        rows.append(
            {
                **candidate,
                "paper_class": verdict.paper_class if verdict else None,
                "rough_implementability": verdict.rough_implementability if verdict else None,
                "keep": verdict.keep if verdict else None,
                "reasoning": verdict.reasoning if verdict else None,
                "outcome": outcome,
            }
        )
    return rows


async def _collect(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Crawl, classify and join. Returns the rows; writing them is the caller's job."""
    settings = get_settings()
    categories = args.categories or settings.triage_categories
    max_per_category = args.max_per_category or settings.triage_max_per_category
    cap = args.cap or settings.triage_max_survivors

    _progress(f"crawling {categories} (max {max_per_category}/category)...")
    candidates = await _crawl(
        categories, max_per_category, args.lookback_days, settings.arxiv_crawl_pause_seconds
    )
    crawled = list(candidates.values())
    _progress(f"classifying {len(crawled)} candidates...")
    verdicts = await _classify(crawled, settings.triage_batch_concurrency)
    return _rows(candidates, verdicts, cap)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="JSONL destination")
    parser.add_argument("--categories", nargs="*", help="default: TRIAGE_CATEGORIES")
    parser.add_argument("--max-per-category", type=int, help="default: TRIAGE_MAX_PER_CATEGORY")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--cap", type=int, help="survivor cap; default: TRIAGE_MAX_SURVIVORS")
    args = parser.parse_args()

    rows = asyncio.run(_collect(args))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    _progress(f"\nwrote {len(rows)} rows to {out}")
    for outcome in ("survived", "capped", "rejected", "no_verdict"):
        _progress(f"  {outcome:<12} {counts.get(outcome, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
