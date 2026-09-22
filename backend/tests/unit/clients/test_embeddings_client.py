"""Tests for EmbeddingsClient (OpenAI text-embedding-3-small through LiteLLM)."""

from unittest.mock import AsyncMock, MagicMock, patch

import litellm
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
    """A LiteLLM EmbeddingResponse-shaped object; items carry an explicit index."""
    items = [{"object": "embedding", "index": i, "embedding": v} for i, v in enumerate(vectors)]
    if shuffle:
        items.reverse()
    return MagicMock(data=items)


def _provider_error(cls: type[Exception], headers: dict | None = None) -> Exception:
    response = MagicMock()
    response.headers = headers or {}
    return cls(
        message="boom", llm_provider="openai", model="text-embedding-3-small", response=response
    )


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
    async def test_passes_model_dimensions_key_and_timeout(self, client: EmbeddingsClient) -> None:
        vectors = [[0.1] * EMBEDDING_DIMENSION, [0.2] * EMBEDDING_DIMENSION]
        with patch(
            "src.clients.embeddings_client.litellm.aembedding",
            new_callable=AsyncMock,
            return_value=_response(vectors, shuffle=True),
        ) as aembedding:
            result = await client._embed_batch(batch=["a", "b"], batch_num=1)

        assert result == vectors  # re-ordered by index despite a shuffled response
        aembedding.assert_awaited_once_with(
            model="openai/text-embedding-3-small",
            input=["a", "b"],
            dimensions=1024,
            api_key="test-key",
            timeout=12.0,
        )

    async def test_rejects_wrong_dimension(self, client: EmbeddingsClient) -> None:
        """drop_params=True could silently drop `dimensions`; a 1536-wide vector must not reach pgvector."""
        with patch(
            "src.clients.embeddings_client.litellm.aembedding",
            new_callable=AsyncMock,
            return_value=_response([[0.1] * 1536]),
        ):
            with pytest.raises(EmbeddingServiceError, match="1024"):
                await client._embed_batch(batch=["a"], batch_num=1)

    async def test_rejects_count_mismatch(self, client: EmbeddingsClient) -> None:
        with patch(
            "src.clients.embeddings_client.litellm.aembedding",
            new_callable=AsyncMock,
            return_value=_response([[0.1] * EMBEDDING_DIMENSION]),
        ):
            with pytest.raises(EmbeddingServiceError, match="Expected 2 embeddings"):
                await client._embed_batch(batch=["a", "b"], batch_num=3)

    async def test_rate_limit_maps_with_retry_after(self, client: EmbeddingsClient) -> None:
        err = _provider_error(litellm.RateLimitError, headers={"retry-after": "30"})
        with patch(
            "src.clients.embeddings_client.litellm.aembedding",
            new_callable=AsyncMock,
            side_effect=err,
        ):
            with pytest.raises(EmbeddingRateLimitError) as exc_info:
                await client._embed_batch(batch=["a"], batch_num=2)
        assert exc_info.value.retry_after == 30.0
        assert "batch 2" in str(exc_info.value)

    async def test_rate_limit_without_header(self, client: EmbeddingsClient) -> None:
        err = _provider_error(litellm.RateLimitError)
        with patch(
            "src.clients.embeddings_client.litellm.aembedding",
            new_callable=AsyncMock,
            side_effect=err,
        ):
            with pytest.raises(EmbeddingRateLimitError) as exc_info:
                await client._embed_batch(batch=["a"], batch_num=1)
        assert exc_info.value.retry_after is None

    async def test_other_provider_errors_become_service_errors(
        self, client: EmbeddingsClient
    ) -> None:
        err = litellm.AuthenticationError(message="bad key", llm_provider="openai", model="m")
        with patch(
            "src.clients.embeddings_client.litellm.aembedding",
            new_callable=AsyncMock,
            side_effect=err,
        ):
            with pytest.raises(EmbeddingServiceError, match="batch 1"):
                await client._embed_batch(batch=["a"], batch_num=1)

    async def test_connection_errors_propagate_for_tenacity(self, client: EmbeddingsClient) -> None:
        err = litellm.APIConnectionError(message="down", llm_provider="openai", model="m")
        with patch(
            "src.clients.embeddings_client.litellm.aembedding",
            new_callable=AsyncMock,
            side_effect=err,
        ):
            with pytest.raises(litellm.APIConnectionError):
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
