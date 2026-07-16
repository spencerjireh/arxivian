# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27"]
# ///
"""GitHub code-gap efficacy spike.

Answers ONE question with data before any scoring-pipeline code is written:

    "Given a paper, can GitHub search find its known implementation,
     and with which query strategy?"

Code gap is the highest-weighted dimension in the scoring rubric
(docs/design/scoring-pipeline.md). If GitHub search cannot reliably surface a paper's
known repo, that top signal is noise and the design needs rethinking. This is an
efficacy question, not a coding question -- so it gets a throwaway experiment, not a
production client.

Run:
    GITHUB_TOKEN=<pat> uv run spikes/github-code-gap/github_code_gap_spike.py

Without a token it still runs the repository-search strategies (heavily rate-limited)
and skips code search, which requires auth. See README.md.

Outputs a per-paper table + a recall@k summary to stdout, and full detail to results.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

HERE = Path(__file__).parent
GOLDEN_PATH = HERE / "golden_papers.json"
RESULTS_PATH = HERE / "results.json"

GITHUB_API = "https://api.github.com"
RECALL_KS = (1, 5, 10)
PER_PAGE = 20  # top-N results we inspect per query

# Search API allows ~30 req/min authenticated, ~10 unauthenticated. Pace to stay under the
# secondary rate limit. Token presence decides spacing.
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
MIN_INTERVAL_S = 2.2 if TOKEN else 6.5

STOPWORDS = {
    "a", "an", "the", "of", "for", "and", "or", "with", "in", "on", "to", "at", "is",
    "are", "as", "by", "from", "via", "using", "we", "our", "into", "how", "what",
    "models", "model", "learning", "networks", "network", "deep", "neural",
}


@dataclass
class StrategyResult:
    name: str
    query: str
    hit_rank: int | None  # 1-based rank of known_repo in results, or None if absent
    top_results: list[str] = field(default_factory=list)  # top full_names, for eyeballing
    error: str | None = None


@dataclass
class PaperResult:
    arxiv_id: str
    title: str
    known_repo: str | None
    has_code: bool
    difficulty: str
    strategies: list[StrategyResult] = field(default_factory=list)

    @property
    def best_rank(self) -> int | None:
        ranks = [s.hit_rank for s in self.strategies if s.hit_rank is not None]
        return min(ranks) if ranks else None


class GitHubSearch:
    """Minimal, rate-limit-aware GitHub Search client for the spike only."""

    def __init__(self, token: str) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "arxivian-code-gap-spike",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(headers=headers, timeout=30.0, base_url=GITHUB_API)
        self._last_call = 0.0
        self.total_requests = 0
        self.rate_limit_hits = 0

    def close(self) -> None:
        self._client.close()

    def _pace(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < MIN_INTERVAL_S:
            time.sleep(MIN_INTERVAL_S - elapsed)

    def search(self, endpoint: str, query: str) -> list[dict[str, Any]] | None:
        """endpoint in {'repositories', 'code'}. Returns items list, or None on error.

        Mirrors the tenacity Retry-After-aware backoff pattern the real
        clients/embeddings_client.py uses (see docs/design/scoring-pipeline.md).
        """
        params = {"q": query, "per_page": PER_PAGE}
        for attempt in range(4):
            self._pace()
            self._last_call = time.monotonic()
            self.total_requests += 1
            try:
                resp = self._client.get(f"/search/{endpoint}", params=params)
            except httpx.HTTPError as exc:
                return None if attempt == 3 else self._backoff(f"transport: {exc}", attempt)

            if resp.status_code == 200:
                return resp.json().get("items", [])

            # 403 (secondary/primary limit) or 429: honor Retry-After / reset, then retry.
            if resp.status_code in (403, 429):
                self.rate_limit_hits += 1
                wait = self._rate_limit_wait(resp)
                sys.stderr.write(f"  rate-limited ({resp.status_code}); sleeping {wait:.0f}s\n")
                time.sleep(wait)
                continue

            if resp.status_code == 422:  # unprocessable query (e.g. too short) -- not retryable
                return []

            self._backoff(f"http {resp.status_code}", attempt)
        return None

    @staticmethod
    def _rate_limit_wait(resp: httpx.Response) -> float:
        retry_after = resp.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            return min(max(float(retry_after), 5.0), 120.0)
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")
        if remaining == "0" and reset and reset.isdigit():
            # reset is an epoch second; sleep until then (bounded).
            delta = float(reset) - time.time() + 2.0
            return min(max(delta, 5.0), 120.0)
        return 20.0

    def _backoff(self, reason: str, attempt: int) -> None:
        wait = min(2.0 * (2**attempt), 30.0)
        sys.stderr.write(f"  {reason}; backoff {wait:.0f}s\n")
        time.sleep(wait)


def title_tokens(title: str, limit: int = 6) -> list[str]:
    raw = "".join(c if c.isalnum() else " " for c in title.lower()).split()
    kept: list[str] = []
    for tok in raw:
        if len(tok) >= 3 and tok not in STOPWORDS and tok not in kept:
            kept.append(tok)
        if len(kept) >= limit:
            break
    return kept


def last_name(author: str) -> str:
    return author.split()[-1] if author.strip() else ""


def rank_of(known_repo: str, items: list[dict[str, Any]], endpoint: str) -> tuple[int | None, list[str]]:
    target = known_repo.lower()
    full_names: list[str] = []
    hit_rank: int | None = None
    for i, item in enumerate(items, start=1):
        if endpoint == "code":
            full = item.get("repository", {}).get("full_name", "")
        else:
            full = item.get("full_name", "")
        full_names.append(full)
        if hit_rank is None and full.lower() == target:
            hit_rank = i
    return hit_rank, full_names[:10]


def run_strategies(gh: GitHubSearch, paper: dict[str, Any]) -> list[StrategyResult]:
    arxiv_id = paper["arxiv_id"]
    known = paper.get("known_repo")
    tokens = title_tokens(paper["title"])
    authors = paper.get("authors", [])
    first_last = last_name(authors[0]) if authors else ""

    plans: list[tuple[str, str, str]] = [
        ("repo_arxiv_id", "repositories", f'"{arxiv_id}"'),
        ("repo_title", "repositories", " ".join(tokens)),
    ]
    if first_last and tokens:
        plans.append(("repo_author", "repositories", f"{first_last} {tokens[0]} {tokens[1] if len(tokens) > 1 else ''}".strip()))
    if TOKEN:
        # Code search inspects file contents (incl. README) -- the arXiv id often appears there.
        plans.append(("code_arxiv_id", "code", f'"{arxiv_id}"'))
    else:
        plans.append(StrategyResult("code_arxiv_id", "<skipped: needs GITHUB_TOKEN>", None))  # type: ignore[arg-type]

    results: list[StrategyResult] = []
    for plan in plans:
        if isinstance(plan, StrategyResult):
            results.append(plan)
            continue
        name, endpoint, query = plan
        items = gh.search(endpoint, query)
        if items is None:
            results.append(StrategyResult(name, query, None, error="request failed"))
            continue
        hit_rank, top = (None, [])
        if known:
            hit_rank, top = rank_of(known, items, endpoint)
        else:
            top = [
                (it.get("repository", {}).get("full_name", "") if endpoint == "code" else it.get("full_name", ""))
                for it in items[:5]
            ]
        results.append(StrategyResult(name, query, hit_rank, top_results=top))
    return results


def recall_at_k(papers: list[PaperResult], k: int, strategy: str | None) -> tuple[int, int]:
    """Returns (hits, denom) over has_code papers. strategy=None -> combined best rank."""
    hits = denom = 0
    for p in papers:
        if not p.has_code or not p.known_repo:
            continue
        denom += 1
        if strategy is None:
            rank = p.best_rank
        else:
            rank = next((s.hit_rank for s in p.strategies if s.name == strategy), None)
        if rank is not None and rank <= k:
            hits += 1
    return hits, denom


def print_report(papers: list[PaperResult], gh: GitHubSearch) -> None:
    print("\n" + "=" * 78)
    print("PER-PAPER (rank of known repo; '-' = not found; blank = no known repo)")
    print("=" * 78)
    strat_names = ["repo_arxiv_id", "repo_title", "repo_author", "code_arxiv_id"]
    header = f"{'arxiv_id':<12} {'diff':<6} " + " ".join(f"{s[:9]:>9}" for s in strat_names) + f"  {'best':>4}"
    print(header)
    print("-" * len(header))
    for p in papers:
        cells = []
        for s in strat_names:
            sr = next((x for x in p.strategies if x.name == s), None)
            if sr is None or not p.known_repo:
                cells.append(f"{'':>9}")
            elif sr.error:
                cells.append(f"{'err':>9}")
            elif sr.hit_rank is None:
                cells.append(f"{'-':>9}")
            else:
                cells.append(f"{sr.hit_rank:>9}")
        best = "" if not p.known_repo else ("-" if p.best_rank is None else str(p.best_rank))
        print(f"{p.arxiv_id:<12} {p.difficulty:<6} " + " ".join(cells) + f"  {best:>4}")

    print("\n" + "=" * 78)
    print("RECALL@k over papers-with-known-code")
    print("=" * 78)
    denom = sum(1 for p in papers if p.has_code and p.known_repo)
    print(f"labeled papers with known code: {denom}\n")
    row = f"{'strategy':<16}" + "".join(f"  recall@{k:<3}" for k in RECALL_KS)
    print(row)
    print("-" * len(row))
    for strat in [*strat_names, None]:
        label = strat or "COMBINED (best)"
        cells = ""
        for k in RECALL_KS:
            h, d = recall_at_k(papers, k, strat)
            cells += f"  {(h / d if d else 0):>7.2f}" if d else f"  {'n/a':>7}"
        print(f"{label:<16}{cells}")

    # False-signal watch: for papers with NO known code, did search return a confident repo?
    gaps = [p for p in papers if not p.has_code]
    if gaps:
        print("\n" + "=" * 78)
        print("FALSE-SIGNAL WATCH (papers with NO known repo -- top repo_arxiv_id hits)")
        print("A genuine code gap should return empty / clearly-unrelated results here.")
        print("=" * 78)
        for p in gaps:
            sr = next((x for x in p.strategies if x.name == "repo_arxiv_id"), None)
            top = ", ".join(sr.top_results[:3]) if sr and sr.top_results else "(none)"
            print(f"{p.arxiv_id:<12} {p.title[:40]:<40} -> {top}")

    print("\n" + "=" * 78)
    combined = recall_at_k(papers, 10, None)
    combined_r = combined[0] / combined[1] if combined[1] else 0.0
    verdict = "PASS" if combined_r >= 0.8 else "INVESTIGATE"
    print(f"VERDICT: combined recall@10 = {combined_r:.2f}  ->  {verdict}")
    print(f"  (decision bar ~0.80; below it, the code-gap signal needs rethinking before")
    print(f"   building clients/github_client.py and the paper_scores schema)")
    print(f"requests: {gh.total_requests}  rate-limit hits: {gh.rate_limit_hits}  "
          f"token: {'yes' if TOKEN else 'NO (code search skipped)'}")
    print("=" * 78 + "\n")


def main() -> int:
    if not GOLDEN_PATH.exists():
        sys.stderr.write(f"missing {GOLDEN_PATH}\n")
        return 1
    golden = json.loads(GOLDEN_PATH.read_text())
    papers_in = golden["papers"]

    if not TOKEN:
        sys.stderr.write(
            "WARNING: GITHUB_TOKEN not set. Running repo-search strategies only "
            "(slow, ~10 req/min) and skipping code search.\n"
        )

    gh = GitHubSearch(TOKEN)
    results: list[PaperResult] = []
    try:
        for i, paper in enumerate(papers_in, start=1):
            sys.stderr.write(f"[{i}/{len(papers_in)}] {paper['arxiv_id']} {paper['title'][:50]}\n")
            strategies = run_strategies(gh, paper)
            results.append(
                PaperResult(
                    arxiv_id=paper["arxiv_id"],
                    title=paper["title"],
                    known_repo=paper.get("known_repo"),
                    has_code=paper.get("has_code", paper.get("known_repo") is not None),
                    difficulty=paper.get("difficulty", "?"),
                    strategies=strategies,
                )
            )
    finally:
        gh.close()

    # Persist full detail.
    RESULTS_PATH.write_text(
        json.dumps(
            {
                "meta": {
                    "requests": gh.total_requests,
                    "rate_limit_hits": gh.rate_limit_hits,
                    "authenticated": bool(TOKEN),
                    "per_page": PER_PAGE,
                },
                "papers": [
                    {
                        "arxiv_id": p.arxiv_id,
                        "title": p.title,
                        "known_repo": p.known_repo,
                        "has_code": p.has_code,
                        "difficulty": p.difficulty,
                        "best_rank": p.best_rank,
                        "strategies": [
                            {
                                "name": s.name,
                                "query": s.query,
                                "hit_rank": s.hit_rank,
                                "top_results": s.top_results,
                                "error": s.error,
                            }
                            for s in p.strategies
                        ],
                    }
                    for p in results
                ],
            },
            indent=2,
        )
    )
    print_report(results, gh)
    print(f"full detail written to {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
