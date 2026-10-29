"""Unit tests for the Anthropic chat client (no network).

Concentrated on the three places Anthropic differs from OpenAI, because those are the whole
reason this is a separate implementation rather than a translation layer: the system prompt
is a top-level parameter, structured output is tool-shaped, and `max_tokens` is mandatory.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, ValidationError

from src.clients.anthropic_client import (
    DEFAULT_MAX_TOKENS,
    AnthropicClient,
    _split_messages,
    _text_of,
)
from src.exceptions import LLMTimeoutError


class SampleResponse(BaseModel):
    answer: str


@pytest.fixture
def client():
    return AnthropicClient(api_key="k", model="anthropic/claude-haiku-4-5-20251001", timeout=5.0)


def _message(text: str = "hi"):
    block = MagicMock()
    block.type = "text"
    block.text = text
    r = MagicMock()
    r.content = [block]
    r.usage = MagicMock(input_tokens=1, output_tokens=2)
    return r


def _tool_use(payload: dict, name: str = "emit_result"):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = payload
    r = MagicMock()
    r.content = [block]
    r.usage = MagicMock(input_tokens=1, output_tokens=2)
    r.stop_reason = "tool_use"
    return r


@pytest.mark.unit
class TestMessageConversion:
    def test_system_turns_are_lifted_out(self):
        system, turns = _split_messages(
            [
                {"role": "system", "content": "be terse"},
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ]
        )
        assert system == "be terse"
        assert turns == [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]

    def test_multiple_system_turns_are_joined_not_dropped(self):
        """The agent graph composes its system prompt from several pieces.

        Keeping only the first would change behaviour with nothing to catch it.
        """
        system, turns = _split_messages(
            [
                {"role": "system", "content": "one"},
                {"role": "system", "content": "two"},
                {"role": "user", "content": "q"},
            ]
        )
        assert system == "one\n\ntwo"
        assert len(turns) == 1

    def test_empty_turns_are_dropped(self):
        """Anthropic rejects empty content blocks."""
        _, turns = _split_messages(
            [{"role": "user", "content": ""}, {"role": "user", "content": "real"}]
        )
        assert turns == [{"role": "user", "content": "real"}]

    def test_content_part_lists_are_flattened(self):
        assert _text_of([{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]) == "ab"
        assert _text_of("plain") == "plain"
        assert _text_of(None) == ""


@pytest.mark.unit
class TestGenerateCompletion:
    async def test_system_goes_top_level_not_into_messages(self, client):
        client._client.messages.create = AsyncMock(return_value=_message("ok"))

        out = await client.generate_completion(
            [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
        )

        assert out == "ok"
        kwargs = client._client.messages.create.await_args.kwargs
        assert kwargs["system"] == "S"
        assert kwargs["messages"] == [{"role": "user", "content": "U"}]
        # The SDK gets the bare id, and max_tokens is always supplied.
        assert kwargs["model"] == "claude-haiku-4-5-20251001"
        assert kwargs["max_tokens"] == 1000

    async def test_no_system_key_when_there_is_no_system_prompt(self, client):
        client._client.messages.create = AsyncMock(return_value=_message())
        await client.generate_completion([{"role": "user", "content": "U"}])
        assert "system" not in client._client.messages.create.await_args.kwargs

    async def test_prompt_caching_marks_the_system_block(self):
        """Opt-in, and only worth it where the prefix recurs (the paper-scoped chat)."""
        c = AnthropicClient(api_key="k", cache_system=True)
        c._client.messages.create = AsyncMock(return_value=_message())

        await c.generate_completion(
            [{"role": "system", "content": "paper context"}, {"role": "user", "content": "q"}]
        )

        assert c._client.messages.create.await_args.kwargs["system"] == [
            {
                "type": "text",
                "text": "paper context",
                "cache_control": {"type": "ephemeral"},
            }
        ]

    async def test_caching_off_sends_a_plain_string(self, client):
        client._client.messages.create = AsyncMock(return_value=_message())
        await client.generate_completion(
            [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}]
        )
        assert client._client.messages.create.await_args.kwargs["system"] == "S"

    async def test_timeout_raises_llm_timeout_error(self):
        c = AnthropicClient(api_key="k", timeout=0.01)

        async def hang(**_):
            import asyncio

            await asyncio.sleep(1)

        c._client.messages.create = hang
        with pytest.raises(LLMTimeoutError) as exc:
            await c.generate_completion([{"role": "user", "content": "q"}])
        assert exc.value.details["provider"] == "anthropic"


@pytest.mark.unit
class TestGenerateStructured:
    async def test_forces_a_tool_and_parses_its_input(self, client):
        client._client.messages.create = AsyncMock(return_value=_tool_use({"answer": "yes"}))

        out = await client.generate_structured([{"role": "user", "content": "q"}], SampleResponse)

        assert out == SampleResponse(answer="yes")
        kwargs = client._client.messages.create.await_args.kwargs
        # Forcing the tool is what makes this structured rather than hopeful.
        assert kwargs["tool_choice"] == {"type": "tool", "name": "emit_result"}
        assert kwargs["tools"][0]["input_schema"] == SampleResponse.model_json_schema()

    async def test_missing_tool_call_raises_rather_than_returning_nothing(self, client):
        """Same contract as the OpenAI client: a failed call must not read as empty data."""
        resp = _message("I would rather not")
        resp.stop_reason = "end_turn"
        client._client.messages.create = AsyncMock(return_value=resp)

        with pytest.raises(ValueError, match="no emit_result call"):
            await client.generate_structured([{"role": "user", "content": "q"}], SampleResponse)

    async def test_invalid_tool_payload_fails_validation(self, client):
        """A malformed tool payload must surface, not be coerced into a half-filled model."""
        client._client.messages.create = AsyncMock(return_value=_tool_use({"wrong": 1}))
        with pytest.raises(ValidationError):
            await client.generate_structured([{"role": "user", "content": "q"}], SampleResponse)

    async def test_an_explicit_cap_overrides_the_default(self, client):
        """This API requires `max_tokens`, so None keeps the default rather than omitting it."""
        client._client.messages.create = AsyncMock(return_value=_tool_use({"answer": "yes"}))

        await client.generate_structured([{"role": "user", "content": "q"}], SampleResponse)
        assert client._client.messages.create.await_args.kwargs["max_tokens"] == DEFAULT_MAX_TOKENS

        await client.generate_structured(
            [{"role": "user", "content": "q"}], SampleResponse, max_tokens=9000
        )
        assert client._client.messages.create.await_args.kwargs["max_tokens"] == 9000
