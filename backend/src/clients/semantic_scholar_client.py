"""Semantic Scholar client -- citation counts and velocity for the demand signal.

Looks up a paper by arXiv ID and returns its citation metrics. Used by the Stage 2
scoring graph's demand dimension (SPE-270) and by the scoped chat agent via
``SemanticScholarTool``.

Mirrors the tenacity ``Retry-After``-aware backoff pattern from
``embeddings_client.py``. Adds a net-new, fail-open Redis cache (no cache pattern
existed in the repo): raw API fields are cached so the time-derived velocity is always
recomputed fresh, and any Redis failure falls through to the live API rather than
breaking scoring.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal

import httpx
import redis.asyncio as aioredis
from pydantic import BaseModel, Field
from tenacity import (
    RetryCallState,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_settings
from src.exceptions import SemanticScholarError, SemanticScholarRateLimitError
from src.utils.logger import get_logger

log = get_logger(__name__)
_tenacity_logger = logging.getLogger(f"{__name__}.retry")

# Provisional demand-band thresholds in citations/month.
# PROVISIONAL -- recalibrate against the real S2 velocity distribution in Phase 1
# (scoring-rubric.md:116). SPE-270's demand node may override this mapping.
DEMAND_BAND_HIGH_THRESHOLD = 3.0
DEMAND_BAND_MED_THRESHOLD = 0.5

_AVG_DAYS_PER_MONTH = 30.44


def _rate_limit_aware_wait(retry_state: RetryCallState) -> float:
    """Return seconds to wait before next retry.

    If the exception carries a ``retry_after`` value (from the Retry-After header),
    use it -- clamped to [10, 120]s.  Otherwise fall back to exponential backoff.
    """
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, SemanticScholarRateLimitError) and exc.retry_after is not None:
        return max(10.0, min(float(exc.retry_after), 120.0))
    return wait_exponential(multiplier=2, min=4, max=30)(retry_state)


def compute_velocity(
    citation_count: int,
    publication_date: str | None,
    now: datetime,
) -> float:
    """Citations per month since publication.

    Uses a one-month floor on elapsed time so brand-new papers are not assigned a
    spuriously huge velocity. Returns 0.0 when the publication date is unknown.
    """
    if not publication_date:
        return 0.0
    try:
        pub = datetime.strptime(publication_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.0
    months = (now - pub).days / _AVG_DAYS_PER_MONTH
    return citation_count / max(months, 1.0)


def to_demand_band(velocity: float) -> Literal["HIGH", "MED", "LOW"]:
    """Bucket citation velocity into a provisional demand band."""
    if velocity >= DEMAND_BAND_HIGH_THRESHOLD:
        return "HIGH"
    if velocity >= DEMAND_BAND_MED_THRESHOLD:
        return "MED"
    return "LOW"


class CitationMetrics(BaseModel):
    """Citation metrics for a paper, derived from a Semantic Scholar lookup."""

    arxiv_id: str
    found: bool = Field(..., description="Whether the paper was found on Semantic Scholar")
    citation_count: int = 0
    influential_citation_count: int = 0
    publication_date: str | None = None
    citations_per_month: float = 0.0
    demand_band: Literal["HIGH", "MED", "LOW"] = "LOW"


class SemanticScholarClient:
    """Client for the Semantic Scholar Graph API (citation metrics by arXiv ID)."""

    def __init__(self, api_key: str = "", cache_ttl_seconds: int = 604800):
        self.api_key = api_key
        self.cache_ttl_seconds = cache_ttl_seconds
        self.base_url = "https://api.semanticscholar.org"
        self._redis: aioredis.Redis | None = None

    # ------------------------------------------------------------------
    # Cache helpers (fail-open: any Redis error falls through to the API)
    # ------------------------------------------------------------------

    def _get_redis(self) -> aioredis.Redis:
        """Lazily create the Redis connection (DB 2, the general cache instance)."""
        if self._redis is None:
            self._redis = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        return self._redis

    @staticmethod
    def _cache_key(arxiv_id: str) -> str:
        return f"s2:paper:{arxiv_id}"

    async def _cache_get(self, arxiv_id: str) -> dict[str, Any] | None:
        """Return cached raw fields, or None on miss / any Redis error."""
        try:
            raw = await self._get_redis().get(self._cache_key(arxiv_id))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            log.warning("s2_cache_get_failed", arxiv_id=arxiv_id, error=str(e))
            return None

    async def _cache_set(self, arxiv_id: str, raw: dict[str, Any]) -> None:
        """Cache raw fields; swallow any Redis error (fail-open)."""
        try:
            await self._get_redis().set(
                self._cache_key(arxiv_id),
                json.dumps(raw),
                ex=self.cache_ttl_seconds,
            )
        except Exception as e:
            log.warning("s2_cache_set_failed", arxiv_id=arxiv_id, error=str(e))

    # ------------------------------------------------------------------
    # HTTP fetch (backoff-aware)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        """Extract ``Retry-After`` header as a float, or None."""
        raw = response.headers.get("retry-after")
        if raw is None:
            return None
        try:
            return float(raw)
        except (ValueError, TypeError):
            return None

    @retry(
        stop=stop_after_attempt(5),
        wait=_rate_limit_aware_wait,
        retry=retry_if_exception_type(
            (SemanticScholarRateLimitError, httpx.ConnectError, httpx.TimeoutException)
        ),
        before_sleep=before_sleep_log(_tenacity_logger, logging.WARNING),
        reraise=True,
    )
    async def _fetch(self, arxiv_id: str, timeout: float = 30.0) -> dict[str, Any]:
        """Fetch raw citation fields for one paper.

        Raises ``SemanticScholarRateLimitError`` on 429 so tenacity can use the
        rate-limit-aware wait strategy. Returns ``found=False`` on 404. Wraps other
        HTTP errors in ``SemanticScholarError``.
        """
        url = f"{self.base_url}/graph/v1/paper/arXiv:{arxiv_id}"
        params = {"fields": "citationCount,influentialCitationCount,publicationDate,year"}
        headers = {"x-api-key": self.api_key} if self.api_key else {}

        log.debug("s2_fetch", arxiv_id=arxiv_id)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params, headers=headers)

            if response.status_code == 429:
                retry_after = self._parse_retry_after(response)
                raise SemanticScholarRateLimitError(
                    message=f"Rate limited on Semantic Scholar lookup for {arxiv_id} (429)",
                    retry_after=retry_after,
                )
            if response.status_code == 404:
                log.info("s2_paper_not_found", arxiv_id=arxiv_id)
                return {
                    "found": False,
                    "citation_count": 0,
                    "influential_citation_count": 0,
                    "publication_date": None,
                }

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise SemanticScholarError(
                    message=f"Semantic Scholar returned {response.status_code} for {arxiv_id}",
                    details={"status_code": response.status_code},
                ) from e

            data = response.json()

        # publicationDate can be absent even on a 200; fall back to <year>-01-01.
        publication_date = data.get("publicationDate")
        if not publication_date and data.get("year"):
            publication_date = f"{data['year']}-01-01"

        return {
            "found": True,
            "citation_count": data.get("citationCount") or 0,
            "influential_citation_count": data.get("influentialCitationCount") or 0,
            "publication_date": publication_date,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_citation_metrics(self, arxiv_id: str) -> CitationMetrics:
        """Return citation metrics for ``arxiv_id``, using the cache when available.

        Velocity and demand band are recomputed fresh on every call (the raw counts
        are what get cached), so a cached entry never serves a stale, time-derived
        velocity.
        """
        raw = await self._cache_get(arxiv_id)
        if raw is None:
            raw = await self._fetch(arxiv_id)
            await self._cache_set(arxiv_id, raw)

        velocity = compute_velocity(
            citation_count=raw["citation_count"],
            publication_date=raw.get("publication_date"),
            now=datetime.now(timezone.utc),
        )
        return CitationMetrics(
            arxiv_id=arxiv_id,
            found=raw["found"],
            citation_count=raw["citation_count"],
            influential_citation_count=raw["influential_citation_count"],
            publication_date=raw.get("publication_date"),
            citations_per_month=round(velocity, 3),
            demand_band=to_demand_band(velocity),
        )
