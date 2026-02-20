"""Tests for JinaEmbeddingsClient rate-limit handling and batching."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from tenacity import stop_after_attempt

from src.clients.embeddings_client import JinaEmbeddingsClient, _rate_limit_aware_wait
from src.exceptions import EmbeddingRateLimitError


@pytest.fixture
def client() -> JinaEmbeddingsClient:
    return JinaEmbeddingsClient(api_key="test-key")


# ------------------------------------------------------------------
# _parse_retry_after
# ------------------------------------------------------------------


class TestParseRetryAfter:
    def test_valid_numeric(self) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.headers = {"retry-after": "42"}
        assert JinaEmbeddingsClient._parse_retry_after(resp) == 42.0

    def test_valid_float(self) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.headers = {"retry-after": "10.5"}
        assert JinaEmbeddingsClient._parse_retry_after(resp) == 10.5

    def test_missing_header(self) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.headers = {}
        assert JinaEmbeddingsClient._parse_retry_after(resp) is None

    def test_non_numeric(self) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.headers = {"retry-after": "not-a-number"}
        assert JinaEmbeddingsClient._parse_retry_after(resp) is None


# ------------------------------------------------------------------
# _rate_limit_aware_wait
# ------------------------------------------------------------------


class TestRateLimitAwareWait:
    def _make_retry_state(self, exception: BaseException | None = None) -> MagicMock:
        state = MagicMock()
        if exception:
            state.outcome.exception.return_value = exception
        else:
            state.outcome = None
        # tenacity also reads retry_state.attempt_number for exponential backoff
        state.attempt_number = 1
        # and secret_number for jitter
        state.retry_object.wait = None
        return state

    def test_uses_retry_after(self) -> None:
        exc = EmbeddingRateLimitError(retry_after=45.0)
        state = self._make_retry_state(exc)
        assert _rate_limit_aware_wait(state) == 45.0

    def test_clamps_low(self) -> None:
        exc = EmbeddingRateLimitError(retry_after=2.0)
        state = self._make_retry_state(exc)
        assert _rate_limit_aware_wait(state) == 10.0

    def test_clamps_high(self) -> None:
        exc = EmbeddingRateLimitError(retry_after=999.0)
        state = self._make_retry_state(exc)
        assert _rate_limit_aware_wait(state) == 120.0

    def test_falls_back_to_exponential_without_retry_after(self) -> None:
        exc = EmbeddingRateLimitError(retry_after=None)
        state = self._make_retry_state(exc)
        wait = _rate_limit_aware_wait(state)
        assert 4.0 <= wait <= 30.0

    def test_falls_back_for_non_rate_limit_exception(self) -> None:
        state = self._make_retry_state(httpx.ConnectError("fail"))
        wait = _rate_limit_aware_wait(state)
        assert 4.0 <= wait <= 30.0


# ------------------------------------------------------------------
# _embed_batch
# ------------------------------------------------------------------


def _mock_response(
    status_code: int = 200,
    json_data: dict | None = None,
    headers: dict | None = None,
) -> httpx.Response:
    """Build a real httpx.Response with the given attributes."""
    if json_data is None:
        json_data = {"data": [{"embedding": [0.1] * 1024}]}
    resp = httpx.Response(
        status_code=status_code,
        json=json_data,
        headers=headers or {},
        request=httpx.Request("POST", "https://api.jina.ai/v1/embeddings"),
    )
    return resp


class TestEmbedBatch:
    async def test_success(self, client: JinaEmbeddingsClient) -> None:
        """Happy path: returns embeddings from response."""
        mock_resp = _mock_response(
            json_data={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]}
        )

        with patch("src.clients.embeddings_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            # Disable retries for unit test speed
            client._embed_batch.retry.stop = stop_after_attempt(1)
            result = await client._embed_batch(
                batch=["text1", "text2"], task="retrieval.passage", batch_num=1
            )

        assert result == [[0.1, 0.2], [0.3, 0.4]]

    async def test_raises_rate_limit_on_429(self, client: JinaEmbeddingsClient) -> None:
        """429 response raises EmbeddingRateLimitError with parsed retry_after."""
        mock_resp = _mock_response(
            status_code=429,
            json_data={"detail": "rate limited"},
            headers={"retry-after": "30"},
        )

        with patch("src.clients.embeddings_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            client._embed_batch.retry.stop = stop_after_attempt(1)
            with pytest.raises(EmbeddingRateLimitError) as exc_info:
                await client._embed_batch(
                    batch=["text"], task="retrieval.passage", batch_num=2
                )

        assert exc_info.value.retry_after == 30.0
        assert "batch 2" in str(exc_info.value)

    async def test_429_without_retry_after(self, client: JinaEmbeddingsClient) -> None:
        """429 without Retry-After header sets retry_after to None."""
        mock_resp = _mock_response(status_code=429, json_data={"detail": "rate limited"})

        with patch("src.clients.embeddings_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            client._embed_batch.retry.stop = stop_after_attempt(1)
            with pytest.raises(EmbeddingRateLimitError) as exc_info:
                await client._embed_batch(
                    batch=["text"], task="retrieval.passage", batch_num=1
                )

        assert exc_info.value.retry_after is None


# ------------------------------------------------------------------
# embed_documents batching
# ------------------------------------------------------------------


class TestEmbedDocuments:
    async def test_batches_at_50(self, client: JinaEmbeddingsClient) -> None:
        """120 texts should produce 3 batches: 50 + 50 + 20."""
        call_sizes: list[int] = []

        async def tracking_batch(
            batch: list[str], task: str, batch_num: int, timeout: float = 60.0
        ) -> list[list[float]]:
            call_sizes.append(len(batch))
            return [[0.1] * 1024] * len(batch)

        mock = AsyncMock(side_effect=tracking_batch)
        with patch.object(client, "_embed_batch", mock):
            result = await client.embed_documents(["text"] * 120)

        assert call_sizes == [50, 50, 20]
        assert len(result) == 120

    async def test_preserves_succeeded_batches(
        self, client: JinaEmbeddingsClient
    ) -> None:
        """Batch 1 succeeds, batch 2 fails -- batch 1 is not re-sent."""
        batch_1_embeddings = [[0.1] * 1024] * 50

        async def batch_side_effect(
            batch: list[str], task: str, batch_num: int, timeout: float = 60.0
        ) -> list[list[float]]:
            if batch_num == 1:
                return batch_1_embeddings
            raise EmbeddingRateLimitError(retry_after=60.0)

        mock = AsyncMock(side_effect=batch_side_effect)
        with patch.object(client, "_embed_batch", mock):
            with pytest.raises(EmbeddingRateLimitError):
                await client.embed_documents(["text"] * 100)

        # Batch 1 called once, batch 2 called once => total 2
        # (retry is inside _embed_batch, which we've mocked out)
        assert mock.call_count == 2


# ------------------------------------------------------------------
# embed_query
# ------------------------------------------------------------------


class TestEmbedQuery:
    async def test_delegates_to_embed_batch(self, client: JinaEmbeddingsClient) -> None:
        """embed_query should delegate to _embed_batch with task=retrieval.query."""
        expected = [0.5] * 1024

        async def mock_batch(
            batch: list[str], task: str, batch_num: int, timeout: float = 60.0
        ) -> list[list[float]]:
            assert task == "retrieval.query"
            assert batch == ["my query"]
            assert batch_num == 1
            assert timeout == 30.0
            return [expected]

        mock = AsyncMock(side_effect=mock_batch)
        with patch.object(client, "_embed_batch", mock):
            result = await client.embed_query("my query")

        assert result == expected
