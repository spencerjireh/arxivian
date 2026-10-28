"""Unit tests for the OpenAI chat client (no network).

Replaces `test_litellm_client.py` (ARX-75). The SDK is stubbed at the client instance, which
is where the real boundary is -- patching `openai.AsyncOpenAI` globally would also hide the
`max_retries=0` choice, and that choice matters: the Celery tasks own their own retry budgets
and a silent SDK retry inside a bounded task spends that budget without saying so.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from src.clients.base_llm_client import model_without_prefix, provider_from_model
from src.clients.openai_client import OpenAIClient
from src.exceptions import LLMTimeoutError


class SampleResponse(BaseModel):
    answer: str


@pytest.fixture
def messages():
    return [{"role": "user", "content": "hi"}]


@pytest.fixture
def client():
    return OpenAIClient(api_key="k", model="openai/gpt-5-nano", timeout=5.0)


def _completion(content: str = "hello", *, tokens: bool = True):
    r = MagicMock()
    r.choices = [MagicMock()]
    r.choices[0].message.content = content
    if tokens:
        r.usage = MagicMock(prompt_tokens=1, completion_tokens=2, total_tokens=3)
    else:
        r.usage = None
    return r


@pytest.mark.unit
class TestModelRouting:
    def test_provider_prefix_is_read(self):
        assert provider_from_model("openai/gpt-5-nano") == "openai"
        assert provider_from_model("anthropic/claude-haiku-4-5-20251001") == "anthropic"

    def test_bare_model_is_treated_as_openai(self):
        """Older config values carry no prefix and must keep working."""
        assert provider_from_model("gpt-5-nano") == "openai"

    def test_prefix_is_stripped_for_the_sdk(self):
        assert model_without_prefix("openai/gpt-5-nano") == "gpt-5-nano"
        assert model_without_prefix("gpt-5-nano") == "gpt-5-nano"

    def test_properties(self, client):
        assert client.provider_name == "openai"
        assert client.model == "openai/gpt-5-nano"


@pytest.mark.unit
class TestGenerateCompletion:
    async def test_returns_content_and_sends_the_bare_model_id(self, client, messages):
        client._client.chat.completions.create = AsyncMock(return_value=_completion("hello"))

        out = await client.generate_completion(messages)

        assert out == "hello"
        kwargs = client._client.chat.completions.create.await_args.kwargs
        # The SDK must not receive the routed `openai/` form.
        assert kwargs["model"] == "gpt-5-nano"

    async def test_missing_usage_does_not_raise(self, client, messages):
        """`usage` is absent when the provider omits it; logging must tolerate that."""
        client._client.chat.completions.create = AsyncMock(
            return_value=_completion("x", tokens=False)
        )
        assert await client.generate_completion(messages) == "x"

    async def test_none_content_becomes_empty_string(self, client, messages):
        client._client.chat.completions.create = AsyncMock(return_value=_completion(None))
        assert await client.generate_completion(messages) == ""

    async def test_model_override_wins(self, client, messages):
        client._client.chat.completions.create = AsyncMock(return_value=_completion())
        await client.generate_completion(messages, model="openai/gpt-4o-mini")
        assert client._client.chat.completions.create.await_args.kwargs["model"] == "gpt-4o-mini"

    async def test_timeout_raises_llm_timeout_error(self, messages):
        c = OpenAIClient(api_key="k", timeout=0.01)

        async def hang(**_):
            import asyncio

            await asyncio.sleep(1)

        c._client.chat.completions.create = hang
        with pytest.raises(LLMTimeoutError) as exc:
            await c.generate_completion(messages)
        # provider lands in `details`, not as an attribute (see exceptions.LLMTimeoutError).
        assert exc.value.details["provider"] == "openai"


@pytest.mark.unit
class TestGenerateStream:
    @staticmethod
    def _chunks(*texts, include_empty_choices: bool = False):
        out = []
        if include_empty_choices:
            # A real stream opens with a chunk carrying no choices; iterating it must not
            # raise an IndexError.
            empty = MagicMock()
            empty.choices = []
            out.append(empty)
        for t in texts:
            c = MagicMock()
            c.choices = [MagicMock()]
            c.choices[0].delta.content = t
            out.append(c)
        return out

    async def _stream_of(self, chunks):
        for c in chunks:
            yield c

    async def test_yields_token_text(self, client, messages):
        chunks = self._chunks("a", "b")
        client._client.chat.completions.create = AsyncMock(return_value=self._stream_of(chunks))
        assert [t async for t in client.generate_stream(messages)] == ["a", "b"]

    async def test_skips_empty_deltas_and_choiceless_chunks(self, client, messages):
        chunks = self._chunks("a", None, "", "b", include_empty_choices=True)
        client._client.chat.completions.create = AsyncMock(return_value=self._stream_of(chunks))
        assert [t async for t in client.generate_stream(messages)] == ["a", "b"]


@pytest.mark.unit
class TestGenerateStructured:
    async def test_returns_the_parsed_model(self, client, messages):
        parsed = SampleResponse(answer="yes")
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.parsed = parsed
        client._client.chat.completions.parse = AsyncMock(return_value=resp)

        out = await client.generate_structured(messages, SampleResponse)

        assert out is parsed
        assert client._client.chat.completions.parse.await_args.kwargs["response_format"] is (
            SampleResponse
        )

    async def test_structured_model_override_is_used(self, messages):
        c = OpenAIClient(api_key="k", model="openai/a", structured_output_model="openai/b")
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.parsed = SampleResponse(answer="y")
        c._client.chat.completions.parse = AsyncMock(return_value=resp)

        await c.generate_structured(messages, SampleResponse)

        assert c._client.chat.completions.parse.await_args.kwargs["model"] == "b"

    async def test_refusal_raises_rather_than_returning_nothing(self, client, messages):
        """A refusal or a length-truncated response must not read as empty data.

        Triage calls this per batch; a None slipping through would look like "no papers
        qualified" instead of "the call failed".
        """
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.parsed = None
        resp.choices[0].message.refusal = "nope"
        client._client.chat.completions.parse = AsyncMock(return_value=resp)

        with pytest.raises(ValueError, match="no parsed object"):
            await client.generate_structured(messages, SampleResponse)
