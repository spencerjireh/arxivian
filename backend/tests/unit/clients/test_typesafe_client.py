"""Tests for TypeSafeClient: answer normalization and SDK error mapping."""

from unittest.mock import AsyncMock, patch

import httpx2
import pytest
from typesafe_sdk import Noul
from typesafe_sdk import TypeSafeAPIConnectionError as SDKConnectionError
from typesafe_sdk import TypeSafeAPIError as SDKAPIError
from typesafe_sdk import TypeSafeRateLimitError as SDKRateLimitError

from src.clients.typesafe_client import TypeSafeClient
from src.exceptions import TypeSafeConnectionError, TypeSafeError, TypeSafeRateLimitError

_QUESTIONS = {"q": Noul(instructions="Is it?")}


class _Answer:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Response:
    def __init__(self):
        self.model = "jev-1.13.0"
        self.usage = _Answer(input_tokens=321, output_tokens=0)
        self.nouls = {"q": _Answer(noul=0.83)}
        self.choices = {
            "c": _Answer(choice="a", probabilities={"a": 0.7, "b": 0.3}, confidence=0.7)
        }
        self.scores = {
            "s": _Answer(
                score=1.3,
                probabilities={0: 0.0, 1: 0.7, 2: 0.3},
                confidence=0.7,
                legend={0: "zero", 1: "one", 2: "two"},
            )
        }


def _patched_sdk(system_one: AsyncMock):
    sdk = AsyncMock()
    sdk.system_one = system_one
    sdk.__aenter__.return_value = sdk
    return patch("src.clients.typesafe_client.AsyncTypeSafeClient", return_value=sdk)


@pytest.fixture
def client() -> TypeSafeClient:
    return TypeSafeClient(api_key="k", model="jev-1.13.0", timeout_seconds=5)


def test_requires_api_key():
    with pytest.raises(TypeSafeError):
        TypeSafeClient(api_key="", model="jev-1.13.0")


@pytest.mark.asyncio
async def test_ask_normalizes_answers(client):
    system_one = AsyncMock(return_value=_Response())
    with _patched_sdk(system_one):
        result = await client.ask({"x": 1}, _QUESTIONS, request_name="t")

    system_one.assert_awaited_once_with({"x": 1}, _QUESTIONS)
    assert result.model == "jev-1.13.0"
    assert result.input_tokens == 321
    assert result.nouls == {"q": 0.83}
    assert result.choices["c"].choice == "a"
    assert result.scores["s"].score == 1.3
    assert result.scores["s"].probabilities == {0: 0.0, 1: 0.7, 2: 0.3}
    assert result.scores["s"].legend == ["zero", "one", "two"]


@pytest.mark.asyncio
async def test_rate_limit_mapped_with_retry_after_seconds(client):
    err = SDKRateLimitError(429, {"error": "slow down"}, httpx2.Headers({"retry-after-ms": "1500"}))
    with _patched_sdk(AsyncMock(side_effect=err)), pytest.raises(TypeSafeRateLimitError) as exc:
        await client.ask("s", _QUESTIONS, request_name="t")
    assert exc.value.retry_after == pytest.approx(1.5)
    assert exc.value.status == 429


@pytest.mark.asyncio
async def test_rate_limit_without_header(client):
    err = SDKRateLimitError(429, None, httpx2.Headers({}))
    with _patched_sdk(AsyncMock(side_effect=err)), pytest.raises(TypeSafeRateLimitError) as exc:
        await client.ask("s", _QUESTIONS, request_name="t")
    assert exc.value.retry_after is None


@pytest.mark.asyncio
async def test_connection_error_mapped(client):
    with _patched_sdk(AsyncMock(side_effect=SDKConnectionError("connect failed"))):
        with pytest.raises(TypeSafeConnectionError):
            await client.ask("s", _QUESTIONS, request_name="t")


@pytest.mark.asyncio
async def test_api_error_mapped_non_retryable(client):
    err = SDKAPIError(422, {"error": "bad criteria"}, httpx2.Headers({}))
    with _patched_sdk(AsyncMock(side_effect=err)), pytest.raises(TypeSafeError) as exc:
        await client.ask("s", _QUESTIONS, request_name="t")
    assert exc.value.status == 422
    assert not isinstance(exc.value, (TypeSafeRateLimitError, TypeSafeConnectionError))
