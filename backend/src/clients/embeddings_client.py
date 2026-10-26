"""OpenAI embeddings client (text-embedding-3-small), on the vendor SDK.

Anthropic has no embeddings API, so unlike the chat clients there is nothing to abstract
here: this talks to OpenAI directly and always will.

Vectors are requested at 1024 dimensions so `chunks.embedding Vector(1024)` and its HNSW
index stay model-independent. Every response is still length-checked: the OpenAI SDK will
not silently drop `dimensions` the way LiteLLM's `drop_params` could (ARX-75), but a
model swap that ignores the parameter would corrupt the index rather than fail, and that
is worth one assertion.
"""

import logging
import math
from typing import Any

import openai
from openai import AsyncOpenAI
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

# No provider prefix: this client is OpenAI-only, so there is nothing to route.
EMBEDDING_MODEL = "text-embedding-3-small"
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
    """Read a numeric Retry-After header off an OpenAI exception, if it has one."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    raw = headers.get("retry-after") if headers is not None else None
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


class EmbeddingsClient:
    """Embeds queries and documents with OpenAI text-embedding-3-small."""

    def __init__(self, api_key: str, model: str = EMBEDDING_MODEL, timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.dimension = EMBEDDING_DIMENSION
        # Retries are tenacity's job below, not the SDK's; two layers would multiply the
        # attempts and blow past the task time limit.
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=0)

    @retry(
        stop=stop_after_attempt(5),
        wait=_rate_limit_aware_wait,
        retry=retry_if_exception_type(
            (EmbeddingRateLimitError, openai.APIConnectionError, openai.APITimeoutError)
        ),
        before_sleep=before_sleep_log(_tenacity_logger, logging.WARNING),
        reraise=True,
    )
    async def _embed_batch(self, batch: list[str], batch_num: int) -> list[list[float]]:
        """Embed one batch; rate limits become ``EmbeddingRateLimitError`` for tenacity."""
        log.debug("embedding batch", batch=batch_num, size=len(batch))
        try:
            response = await self._client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimension,
            )
        except openai.RateLimitError as e:
            raise EmbeddingRateLimitError(
                message=f"Rate limited on batch {batch_num} (429)",
                retry_after=_retry_after_from(e),
            ) from e
        except (openai.APIConnectionError, openai.APITimeoutError):
            # Re-raised for tenacity to retry; everything else is terminal.
            raise
        except Exception as e:
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
