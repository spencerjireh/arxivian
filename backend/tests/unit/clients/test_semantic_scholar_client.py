"""Tests for SemanticScholarClient: velocity/band helpers, fetch, and fail-open cache."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from tenacity import stop_after_attempt

from src.clients.semantic_scholar_client import (
    CitationMetrics,
    SemanticScholarClient,
    _rate_limit_aware_wait,
    compute_velocity,
    to_demand_band,
)
from src.exceptions import SemanticScholarError, SemanticScholarRateLimitError


@pytest.fixture
def client() -> SemanticScholarClient:
    return SemanticScholarClient(api_key="test-key", cache_ttl_seconds=100)


# ------------------------------------------------------------------
# compute_velocity
# ------------------------------------------------------------------


class TestComputeVelocity:
    _now = datetime(2024, 1, 1, tzinfo=timezone.utc)

    def test_basic_velocity(self) -> None:
        # ~12 months elapsed, 120 citations -> ~10/month
        v = compute_velocity(120, "2023-01-01", self._now)
        assert 9.5 <= v <= 10.5

    def test_one_month_floor_for_recent_paper(self) -> None:
        # Published "yesterday": elapsed < 1 month, floored to 1 -> velocity == count
        v = compute_velocity(30, "2023-12-20", self._now)
        assert v == 30.0

    def test_none_publication_date_returns_zero(self) -> None:
        assert compute_velocity(100, None, self._now) == 0.0

    def test_malformed_publication_date_returns_zero(self) -> None:
        assert compute_velocity(100, "not-a-date", self._now) == 0.0

    def test_zero_citations(self) -> None:
        assert compute_velocity(0, "2023-01-01", self._now) == 0.0


# ------------------------------------------------------------------
# to_demand_band
# ------------------------------------------------------------------


class TestToDemandBand:
    def test_high(self) -> None:
        assert to_demand_band(3.0) == "HIGH"
        assert to_demand_band(50.0) == "HIGH"

    def test_med(self) -> None:
        assert to_demand_band(0.5) == "MED"
        assert to_demand_band(2.9) == "MED"

    def test_low(self) -> None:
        assert to_demand_band(0.49) == "LOW"
        assert to_demand_band(0.0) == "LOW"


# ------------------------------------------------------------------
# _parse_retry_after / _rate_limit_aware_wait
# ------------------------------------------------------------------


class TestParseRetryAfter:
    def test_valid_numeric(self) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.headers = {"retry-after": "42"}
        assert SemanticScholarClient._parse_retry_after(resp) == 42.0

    def test_missing_header(self) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.headers = {}
        assert SemanticScholarClient._parse_retry_after(resp) is None

    def test_non_numeric(self) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.headers = {"retry-after": "soon"}
        assert SemanticScholarClient._parse_retry_after(resp) is None


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

    def test_uses_retry_after_clamped(self) -> None:
        state = self._make_retry_state(SemanticScholarRateLimitError(retry_after=45.0))
        assert _rate_limit_aware_wait(state) == 45.0

    def test_clamps_low(self) -> None:
        state = self._make_retry_state(SemanticScholarRateLimitError(retry_after=1.0))
        assert _rate_limit_aware_wait(state) == 10.0

    def test_falls_back_to_exponential(self) -> None:
        state = self._make_retry_state(httpx.ConnectError("fail"))
        assert 4.0 <= _rate_limit_aware_wait(state) <= 30.0


# ------------------------------------------------------------------
# _fetch
# ------------------------------------------------------------------


def _mock_response(
    status_code: int = 200,
    json_data: dict | None = None,
    headers: dict | None = None,
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_data if json_data is not None else {},
        headers=headers or {},
        request=httpx.Request("GET", "https://api.semanticscholar.org/graph/v1/paper/arXiv:x"),
    )


def _patch_http(mock_resp: httpx.Response):
    """Patch httpx.AsyncClient so client.get returns mock_resp."""
    ctx = patch("src.clients.semantic_scholar_client.httpx.AsyncClient")
    mock_cls = ctx.start()
    mock_http = AsyncMock()
    mock_http.get.return_value = mock_resp
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_cls.return_value = mock_http
    return ctx


class TestFetch:
    async def test_success_parses_fields(self, client: SemanticScholarClient) -> None:
        resp = _mock_response(
            json_data={
                "citationCount": 120,
                "influentialCitationCount": 15,
                "publicationDate": "2023-01-01",
                "year": 2023,
            }
        )
        ctx = _patch_http(resp)
        try:
            client._fetch.retry.stop = stop_after_attempt(1)
            raw = await client._fetch("2301.00001")
        finally:
            ctx.stop()

        assert raw == {
            "found": True,
            "citation_count": 120,
            "influential_citation_count": 15,
            "publication_date": "2023-01-01",
        }

    async def test_missing_publication_date_falls_back_to_year(
        self, client: SemanticScholarClient
    ) -> None:
        resp = _mock_response(json_data={"citationCount": 5, "year": 2022})
        ctx = _patch_http(resp)
        try:
            client._fetch.retry.stop = stop_after_attempt(1)
            raw = await client._fetch("2201.00001")
        finally:
            ctx.stop()

        assert raw["publication_date"] == "2022-01-01"

    async def test_429_raises_rate_limit(self, client: SemanticScholarClient) -> None:
        resp = _mock_response(status_code=429, headers={"retry-after": "30"})
        ctx = _patch_http(resp)
        try:
            client._fetch.retry.stop = stop_after_attempt(1)
            with pytest.raises(SemanticScholarRateLimitError) as exc_info:
                await client._fetch("2301.00001")
        finally:
            ctx.stop()

        assert exc_info.value.retry_after == 30.0

    async def test_404_returns_not_found(self, client: SemanticScholarClient) -> None:
        resp = _mock_response(status_code=404)
        ctx = _patch_http(resp)
        try:
            client._fetch.retry.stop = stop_after_attempt(1)
            raw = await client._fetch("2301.99999")
        finally:
            ctx.stop()

        assert raw["found"] is False
        assert raw["citation_count"] == 0

    async def test_500_wrapped_in_semantic_scholar_error(
        self, client: SemanticScholarClient
    ) -> None:
        resp = _mock_response(status_code=500)
        ctx = _patch_http(resp)
        try:
            client._fetch.retry.stop = stop_after_attempt(1)
            with pytest.raises(SemanticScholarError):
                await client._fetch("2301.00001")
        finally:
            ctx.stop()


# ------------------------------------------------------------------
# get_citation_metrics -- cache behavior (fail-open)
# ------------------------------------------------------------------


_RAW = {
    "found": True,
    "citation_count": 120,
    "influential_citation_count": 15,
    "publication_date": "2023-01-01",
}


class TestGetCitationMetricsCache:
    async def test_cache_hit_skips_fetch(self, client: SemanticScholarClient) -> None:
        client._redis = AsyncMock()
        client._redis.get.return_value = json.dumps(_RAW)

        with patch.object(client, "_fetch", AsyncMock()) as mock_fetch:
            metrics = await client.get_citation_metrics("2301.00001")

        mock_fetch.assert_not_called()
        client._redis.set.assert_not_called()
        assert isinstance(metrics, CitationMetrics)
        assert metrics.citation_count == 120
        assert metrics.found is True

    async def test_cache_miss_populates_cache(self, client: SemanticScholarClient) -> None:
        client._redis = AsyncMock()
        client._redis.get.return_value = None

        with patch.object(client, "_fetch", AsyncMock(return_value=dict(_RAW))) as mock_fetch:
            metrics = await client.get_citation_metrics("2301.00001")

        mock_fetch.assert_awaited_once()
        client._redis.set.assert_awaited_once()
        # TTL forwarded from constructor
        assert client._redis.set.call_args.kwargs["ex"] == 100
        assert metrics.citation_count == 120

    async def test_fail_open_on_redis_get_error(self, client: SemanticScholarClient) -> None:
        client._redis = AsyncMock()
        client._redis.get.side_effect = RuntimeError("redis down")

        with patch.object(client, "_fetch", AsyncMock(return_value=dict(_RAW))) as mock_fetch:
            metrics = await client.get_citation_metrics("2301.00001")

        # Redis get failed -> fell through to the live API
        mock_fetch.assert_awaited_once()
        assert metrics.citation_count == 120

    async def test_fail_open_on_redis_set_error(self, client: SemanticScholarClient) -> None:
        client._redis = AsyncMock()
        client._redis.get.return_value = None
        client._redis.set.side_effect = RuntimeError("redis down")

        with patch.object(client, "_fetch", AsyncMock(return_value=dict(_RAW))):
            metrics = await client.get_citation_metrics("2301.00001")

        # Set failure is swallowed; metrics still returned
        assert metrics.found is True
        assert metrics.demand_band in {"HIGH", "MED", "LOW"}
