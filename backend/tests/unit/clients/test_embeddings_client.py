"""Tests for EmbeddingsClient (OpenAI text-embedding-3-small, on the vendor SDK).

The SDK is stubbed on the client instance rather than patched globally, so the stub sits at
the same boundary production uses (ARX-75).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest
from tenacity import stop_after_attempt

from src.clients.embeddings_client import (
    BATCH_SIZE,
    EMBEDDING_DIMENSION,
    EmbeddingsClient,
    _rate_limit_aware_wait,
)
from src.exceptions import EmbeddingRateLimitError, EmbeddingServiceError


@pytest.fixture
def client() -> EmbeddingsClient:
    c = EmbeddingsClient(api_key="test-key", timeout=12.0)
    c._embed_batch.retry.stop = stop_after_attempt(1)  # no retry latency in unit tests
    return c


def _response(vectors: list[list[float]], shuffle: bool = False) -> MagicMock:
    """An OpenAI CreateEmbeddingResponse-shaped object; items carry an explicit index."""
    items = [{"object": "embedding", "index": i, "embedding": v} for i, v in enumerate(vectors)]
    if shuffle:
        items.reverse()
    return MagicMock(data=items)


def _provider_error(cls: type[Exception], headers: dict | None = None) -> Exception:
    """An openai SDK error carrying a response, so `_retry_after_from` has a header to read."""
    response = MagicMock()
    response.headers = headers or {}
    return cls("boom", response=response, body=None)


class TestRateLimitAwareWait:
    def _make_retry_state(self, exception: BaseException | None = None) -> MagicMock:
        state = MagicMock()
        if exception:
            state.outcome.exception.return_value = exception
        else:
            state.outcome = None
        state.attempt_number = 1
        state.retry_object.wait = None
        return state

    def test_uses_retry_after(self) -> None:
        assert (
            _rate_limit_aware_wait(
                self._make_retry_state(EmbeddingRateLimitError(retry_after=45.0))
            )
            == 45.0
        )

    def test_clamps_low_and_high(self) -> None:
        assert (
            _rate_limit_aware_wait(self._make_retry_state(EmbeddingRateLimitError(retry_after=2.0)))
            == 10.0
        )
        assert (
            _rate_limit_aware_wait(
                self._make_retry_state(EmbeddingRateLimitError(retry_after=999.0))
            )
            == 120.0
        )

    def test_falls_back_to_exponential(self) -> None:
        for exc in (EmbeddingRateLimitError(retry_after=None), RuntimeError("fail")):
            assert 4.0 <= _rate_limit_aware_wait(self._make_retry_state(exc)) <= 30.0


class TestEmbedBatch:
    async def test_passes_model_and_dimensions_and_reorders_by_index(
        self, client: EmbeddingsClient
    ) -> None:
        """`api_key` and `timeout` are client-level on the SDK, not per-call as under LiteLLM.

        `dimensions` still has to be on every call: it is what keeps vectors at 1024 so
        `chunks.embedding Vector(1024)` and its HNSW index stay valid.
        """
        vectors = [[0.1] * EMBEDDING_DIMENSION, [0.2] * EMBEDDING_DIMENSION]
        with patch.object(
            client._client.embeddings,
            "create",
            new_callable=AsyncMock,
            return_value=_response(vectors, shuffle=True),
        ) as create:
            result = await client._embed_batch(batch=["a", "b"], batch_num=1)

        assert result == vectors  # re-ordered by index despite a shuffled response
        create.assert_awaited_once_with(
            model="text-embedding-3-small",
            input=["a", "b"],
            dimensions=EMBEDDING_DIMENSION,
        )
        assert client._client.api_key == "test-key"
        # Retries are tenacity's; the SDK must not add its own on top.
        assert client._client.max_retries == 0

    async def test_rejects_wrong_dimension(self, client: EmbeddingsClient) -> None:
        """drop_params=True could silently drop `dimensions`; a 1536-wide vector must not reach pgvector."""
        with patch.object(
            client._client.embeddings,
            "create",
            new_callable=AsyncMock,
            return_value=_response([[0.1] * 1536]),
        ):
            with pytest.raises(EmbeddingServiceError, match="1024"):
                await client._embed_batch(batch=["a"], batch_num=1)

    async def test_rejects_count_mismatch(self, client: EmbeddingsClient) -> None:
        with patch.object(
            client._client.embeddings,
            "create",
            new_callable=AsyncMock,
            return_value=_response([[0.1] * EMBEDDING_DIMENSION]),
        ):
            with pytest.raises(EmbeddingServiceError, match="Expected 2 embeddings"):
                await client._embed_batch(batch=["a", "b"], batch_num=3)

    async def test_rate_limit_maps_with_retry_after(self, client: EmbeddingsClient) -> None:
        err = _provider_error(openai.RateLimitError, headers={"retry-after": "30"})
        with patch.object(
            client._client.embeddings,
            "create",
            new_callable=AsyncMock,
            side_effect=err,
        ):
            with pytest.raises(EmbeddingRateLimitError) as exc_info:
                await client._embed_batch(batch=["a"], batch_num=2)
        assert exc_info.value.retry_after == 30.0
        assert "batch 2" in str(exc_info.value)

    async def test_rate_limit_without_header(self, client: EmbeddingsClient) -> None:
        err = _provider_error(openai.RateLimitError)
        with patch.object(
            client._client.embeddings,
            "create",
            new_callable=AsyncMock,
            side_effect=err,
        ):
            with pytest.raises(EmbeddingRateLimitError) as exc_info:
                await client._embed_batch(batch=["a"], batch_num=1)
        assert exc_info.value.retry_after is None

    async def test_other_provider_errors_become_service_errors(
        self, client: EmbeddingsClient
    ) -> None:
        err = _provider_error(openai.AuthenticationError)
        with patch.object(
            client._client.embeddings,
            "create",
            new_callable=AsyncMock,
            side_effect=err,
        ):
            with pytest.raises(EmbeddingServiceError, match="batch 1"):
                await client._embed_batch(batch=["a"], batch_num=1)

    async def test_connection_errors_propagate_for_tenacity(self, client: EmbeddingsClient) -> None:
        err = openai.APIConnectionError(request=MagicMock())
        with patch.object(
            client._client.embeddings,
            "create",
            new_callable=AsyncMock,
            side_effect=err,
        ):
            with pytest.raises(openai.APIConnectionError):
                await client._embed_batch(batch=["a"], batch_num=1)


class TestEmbedDocuments:
    async def test_batches_at_batch_size(self, client: EmbeddingsClient) -> None:
        call_sizes: list[int] = []

        async def tracking_batch(batch: list[str], batch_num: int) -> list[list[float]]:
            call_sizes.append(len(batch))
            return [[0.1] * EMBEDDING_DIMENSION] * len(batch)

        with patch.object(client, "_embed_batch", AsyncMock(side_effect=tracking_batch)):
            result = await client.embed_documents(["text"] * (2 * BATCH_SIZE + 20))

        assert call_sizes == [BATCH_SIZE, BATCH_SIZE, 20]
        assert len(result) == 2 * BATCH_SIZE + 20

    async def test_preserves_succeeded_batches(self, client: EmbeddingsClient) -> None:
        async def batch_side_effect(batch: list[str], batch_num: int) -> list[list[float]]:
            if batch_num == 1:
                return [[0.1] * EMBEDDING_DIMENSION] * len(batch)
            raise EmbeddingRateLimitError(retry_after=60.0)

        mock = AsyncMock(side_effect=batch_side_effect)
        with patch.object(client, "_embed_batch", mock):
            with pytest.raises(EmbeddingRateLimitError):
                await client.embed_documents(["text"] * (2 * BATCH_SIZE))
        assert mock.call_count == 2


class TestEmbedQuery:
    async def test_returns_single_vector(self, client: EmbeddingsClient) -> None:
        expected = [0.5] * EMBEDDING_DIMENSION
        mock = AsyncMock(return_value=[expected])
        with patch.object(client, "_embed_batch", mock):
            assert await client.embed_query("my query") == expected
        mock.assert_awaited_once_with(batch=["my query"], batch_num=1)
