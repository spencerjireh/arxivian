"""OpenAI embeddings client (text-embedding-3-small through LiteLLM).

Vectors are requested at 1024 dimensions so `chunks.embedding Vector(1024)` and its HNSW
index are model-independent. LiteLLM runs with `drop_params = True` (see
`litellm_client.py`), which would silently discard `dimensions` for a provider that lacks
it and yield 1536-wide vectors, so every response is length-checked here.
"""

import logging
import math
from typing import Any

import litellm
from tenacity import (
    RetryCallState,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.exceptions import EmbeddingRateLimitError, EmbeddingServiceError
from src.utils.logger import get_logger

log = get_logger(__name__)
_tenacity_logger = logging.getLogger(f"{__name__}.retry")

EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSION = 1024
# OpenAI accepts up to 2048 inputs per call; 100 keeps a retry cheap and a request small.
BATCH_SIZE = 100


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


def _retry_after_from(exc: BaseException) -> float | None:
    """Read a numeric Retry-After header off a LiteLLM/OpenAI exception, if it has one."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    raw = headers.get("retry-after") if headers is not None else None
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


class EmbeddingsClient:
    """Embeds queries and documents with OpenAI text-embedding-3-small via LiteLLM."""

    def __init__(self, api_key: str, model: str = EMBEDDING_MODEL, timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.dimension = EMBEDDING_DIMENSION

    @retry(
        stop=stop_after_attempt(5),
        wait=_rate_limit_aware_wait,
        retry=retry_if_exception_type(
            (EmbeddingRateLimitError, litellm.APIConnectionError, litellm.Timeout)
        ),
        before_sleep=before_sleep_log(_tenacity_logger, logging.WARNING),
        reraise=True,
    )
    async def _embed_batch(self, batch: list[str], batch_num: int) -> list[list[float]]:
        """Embed one batch; rate limits become ``EmbeddingRateLimitError`` for tenacity."""
        log.debug("embedding batch", batch=batch_num, size=len(batch))
        try:
            response = await litellm.aembedding(
                model=self.model,
                input=batch,
                dimensions=self.dimension,
                api_key=self.api_key,
                timeout=self.timeout,
            )
        except litellm.RateLimitError as e:
            raise EmbeddingRateLimitError(
                message=f"Rate limited on batch {batch_num} (429)",
                retry_after=_retry_after_from(e),
            ) from e
        except (litellm.APIConnectionError, litellm.Timeout):
            raise
        except Exception as e:  # provider errors are not one litellm base class
            raise EmbeddingServiceError(
                f"Embedding request failed on batch {batch_num}: {e}"
            ) from e

        items: list[Any] = sorted(response.data, key=_item_index)
        embeddings = [_item_embedding(item) for item in items]
        if len(embeddings) != len(batch):
            raise EmbeddingServiceError(
                f"Expected {len(batch)} embeddings on batch {batch_num}, got {len(embeddings)}"
            )
        for vector in embeddings:
            if len(vector) != self.dimension:
                raise EmbeddingServiceError(
                    f"Expected {self.dimension}-dimensional embeddings, got {len(vector)}"
                )
        return embeddings

    async def embed_query(self, query: str) -> list[float]:
        """Embed a search query; returns a 1024-dimensional vector."""
        log.debug("embedding query", query_len=len(query))
        embeddings = await self._embed_batch(batch=[query], batch_num=1)
        return embeddings[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents in batches; retry is per batch, so succeeded batches are not re-sent."""
        total_batches = math.ceil(len(texts) / BATCH_SIZE)
        log.info("embedding documents", count=len(texts), batches=total_batches)

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            all_embeddings.extend(
                await self._embed_batch(batch=batch, batch_num=i // BATCH_SIZE + 1)
            )

        log.info("documents embedded", count=len(all_embeddings))
        return all_embeddings


def _item_index(item: Any) -> int:
    return int(item["index"] if isinstance(item, dict) else item.index)


def _item_embedding(item: Any) -> list[float]:
    return list(item["embedding"] if isinstance(item, dict) else item.embedding)
