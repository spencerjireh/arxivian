"""Jina AI embeddings client."""

import logging
import math

import httpx
from tenacity import (
    RetryCallState,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.exceptions import EmbeddingRateLimitError
from src.utils.logger import get_logger

log = get_logger(__name__)
_tenacity_logger = logging.getLogger(f"{__name__}.retry")


def _rate_limit_aware_wait(retry_state: RetryCallState) -> float:
    """Return seconds to wait before next retry.

    If the exception carries a ``retry_after`` value (from the Retry-After
    header), use it -- clamped to [10, 120]s.  Otherwise fall back to
    exponential backoff (4-30s, multiplier 2).
    """
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, EmbeddingRateLimitError) and exc.retry_after is not None:
        return max(10.0, min(float(exc.retry_after), 120.0))
    return wait_exponential(multiplier=2, min=4, max=30)(retry_state)


class JinaEmbeddingsClient:
    """Client for Jina AI embeddings API."""

    def __init__(self, api_key: str, model: str = "jina-embeddings-v3"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.jina.ai/v1/embeddings"
        self.dimension = 1024

    # ------------------------------------------------------------------
    # Internal helpers
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
            (EmbeddingRateLimitError, httpx.ConnectError, httpx.TimeoutException)
        ),
        before_sleep=before_sleep_log(_tenacity_logger, logging.WARNING),
        reraise=True,
    )
    async def _embed_batch(
        self,
        batch: list[str],
        task: str,
        batch_num: int,
        timeout: float = 60.0,
    ) -> list[list[float]]:
        """Embed a single batch with retry logic.

        Raises ``EmbeddingRateLimitError`` on 429 so tenacity can use the
        rate-limit-aware wait strategy.
        """
        log.debug("embedding batch", batch=batch_num, size=len(batch), task=task)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "task": task,
                    "input": batch,
                },
            )

            if response.status_code == 429:
                retry_after = self._parse_retry_after(response)
                raise EmbeddingRateLimitError(
                    message=f"Rate limited on batch {batch_num} (429)",
                    retry_after=retry_after,
                )

            response.raise_for_status()
            data = response.json()

        return [item["embedding"] for item in data["data"]]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query.

        Returns a 1024-dimensional embedding vector.
        """
        log.debug("embedding query", query_len=len(query))
        embeddings = await self._embed_batch(
            batch=[query], task="retrieval.query", batch_num=1, timeout=30.0
        )
        return embeddings[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple documents.

        Processes in batches of 50.  Retry is per-batch, so already-succeeded
        batches are never re-sent.
        """
        batch_size = 50
        total_batches = math.ceil(len(texts) / batch_size)

        log.info("embedding documents", count=len(texts), batches=total_batches)

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_num = i // batch_size + 1
            embeddings = await self._embed_batch(
                batch=batch, task="retrieval.passage", batch_num=batch_num
            )
            all_embeddings.extend(embeddings)

        log.info("documents embedded", count=len(all_embeddings))
        return all_embeddings
