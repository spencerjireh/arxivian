"""Anthropic chat client, on the vendor SDK (ARX-75).

Three things differ from OpenAI and are the reason this is a separate implementation rather
than a translation layer:

* **The system prompt is a top-level parameter**, not a message with `role="system"`. Callers
  build OpenAI-shaped messages, so `_split_messages` lifts the system turns out.
* **Structured output is tool-shaped.** There is no `response_format`; the reliable pattern is
  a single tool whose `input_schema` is the Pydantic JSON schema, with `tool_choice` forcing
  it, and the model's tool input read back as the object. That is sturdier than asking for
  JSON in prose and parsing it, which is what a normalising layer falls back to.
* **`max_tokens` is required**, so there is no "unbounded" call to inherit by accident.

Prompt caching is opt-in via `cache_system`. It matters for the paper-scoped chat, which
re-sends the same paper context on every turn -- the one case where the repeated prefix is
large and identical. It is off by default because a cache write costs more than a plain read,
so it only pays where the prefix actually recurs.
"""

from collections.abc import AsyncIterator
from typing import Any, TypeVar

from anthropic import AsyncAnthropic
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from src.clients.base_llm_client import ANTHROPIC, BaseLLMClient, model_without_prefix
from src.utils.logger import get_logger, truncate

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_MAX_TOKENS = 4096
# Name of the synthetic tool used to force structured output. Arbitrary but stable: it shows
# up in traces, so it should read as intent rather than as a real capability.
_STRUCTURED_TOOL = "emit_result"


def _text_of(content: Any) -> str:
    """Flatten OpenAI-shaped message content to text.

    A content part list (the multimodal shape) is reduced to its text parts; anything else is
    stringified. Nothing in this codebase sends images today, so this is a guard rather than a
    feature.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [p.get("text", "") for p in content if isinstance(p, dict) and "text" in p]
        return "".join(parts)
    return "" if content is None else str(content)


def _split_messages(
    messages: list[ChatCompletionMessageParam],
) -> tuple[str, list[dict[str, Any]]]:
    """Separate system turns from the conversation.

    Multiple system messages are joined rather than dropped: the agent graph composes its
    system prompt from several pieces, and silently keeping only the first would change
    behaviour in a way no test would catch.
    """
    system_parts: list[str] = []
    turns: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        text = _text_of(msg.get("content"))
        if role == "system" and text:
            system_parts.append(text)
        # Anthropic rejects empty content blocks, so an empty turn is dropped rather than sent.
        elif role in ("user", "assistant") and text:
            turns.append({"role": role, "content": text})
    return "\n\n".join(system_parts), turns


class AnthropicClient(BaseLLMClient):
    """Chat, streaming and structured output against the Anthropic API."""

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-haiku-4-5-20251001",
        timeout: float = 60.0,
        structured_output_model: str | None = None,
        cache_system: bool = False,
    ):
        self._model = model
        self.default_timeout = timeout
        self._structured_output_model = structured_output_model
        self._cache_system = cache_system
        # As with OpenAI: no SDK-level retries, because the Celery tasks own their budgets.
        self._client = AsyncAnthropic(api_key=api_key, max_retries=0)

    @property
    def provider_name(self) -> str:
        return ANTHROPIC

    @property
    def model(self) -> str:
        return self._model

    def _system_param(self, system: str) -> Any:
        """The system prompt, as a cacheable block when caching is on."""
        if not system:
            return None
        if not self._cache_system:
            return system
        return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    async def generate_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        timeout: float | None = None,
    ) -> str:
        model_to_use = model_without_prefix(model or self._model)
        effective_timeout = timeout if timeout is not None else self.default_timeout
        system, turns = _split_messages(messages)

        log.debug(
            "anthropic request",
            model=model_to_use,
            messages=len(turns),
            system=bool(system),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=effective_timeout,
        )

        kwargs: dict[str, Any] = {
            "model": model_to_use,
            "messages": turns,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if (system_param := self._system_param(system)) is not None:
            kwargs["system"] = system_param

        async with self._timeout(effective_timeout):
            response = await self._client.messages.create(**kwargs)

        content = "".join(block.text for block in response.content if block.type == "text")
        usage = response.usage

        log.debug(
            "anthropic response",
            model=model_to_use,
            content=truncate(content, 2000),
            prompt_tokens=usage.input_tokens if usage else None,
            completion_tokens=usage.output_tokens if usage else None,
            # Present only when prompt caching is in play; worth logging because it is the
            # whole reason `cache_system` exists.
            cache_read=getattr(usage, "cache_read_input_tokens", None) if usage else None,
            cache_write=getattr(usage, "cache_creation_input_tokens", None) if usage else None,
        )
        return content

    async def generate_stream(
        self,
        messages: list[ChatCompletionMessageParam],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        timeout: float | None = None,
    ) -> AsyncIterator[str]:
        model_to_use = model_without_prefix(model or self._model)
        effective_timeout = timeout if timeout is not None else self.default_timeout
        system, turns = _split_messages(messages)

        log.debug(
            "anthropic stream request",
            model=model_to_use,
            messages=len(turns),
            timeout=effective_timeout,
        )

        kwargs: dict[str, Any] = {
            "model": model_to_use,
            "messages": turns,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if (system_param := self._system_param(system)) is not None:
            kwargs["system"] = system_param

        # Bounds the whole stream, matching the OpenAI client: a generation that stalls
        # halfway through is the failure that strands a chat turn.
        async with (
            self._timeout(effective_timeout),
            self._client.messages.stream(**kwargs) as stream,
        ):
            async for text in stream.text_stream:
                if text:
                    yield text

    async def generate_structured(
        self,
        messages: list[ChatCompletionMessageParam],
        response_format: type[T],
        model: str | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
    ) -> T:
        model_to_use = model_without_prefix(model or self._structured_output_model or self._model)
        effective_timeout = timeout if timeout is not None else self.default_timeout
        system, turns = _split_messages(messages)
        # Unlike OpenAI this API has no "unbounded" option, so a caller passing None still
        # gets a cap. A batched caller whose schema holds a list must size it explicitly.
        effective_max_tokens = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS

        log.debug(
            "anthropic structured request",
            model=model_to_use,
            response_format=response_format.__name__,
            max_tokens=effective_max_tokens,
            timeout=effective_timeout,
        )

        tool = {
            "name": _STRUCTURED_TOOL,
            "description": f"Return the result as {response_format.__name__}.",
            "input_schema": response_format.model_json_schema(),
        }
        kwargs: dict[str, Any] = {
            "model": model_to_use,
            "messages": turns,
            "max_tokens": effective_max_tokens,
            "tools": [tool],
            # Forcing the tool is what makes this structured rather than hopeful.
            "tool_choice": {"type": "tool", "name": _STRUCTURED_TOOL},
        }
        if (system_param := self._system_param(system)) is not None:
            kwargs["system"] = system_param

        async with self._timeout(effective_timeout):
            response = await self._client.messages.create(**kwargs)

        payload = next(
            (
                b.input
                for b in response.content
                if b.type == "tool_use" and b.name == _STRUCTURED_TOOL
            ),
            None,
        )
        if payload is None:
            # Treated as a failed call, not as empty data: a silently empty verdict set would
            # read as "nothing qualified" to triage.
            raise ValueError(
                f"Structured output returned no {_STRUCTURED_TOOL} call "
                f"(stop_reason={response.stop_reason})"
            )

        parsed = response_format.model_validate(payload)
        log.debug(
            "anthropic structured response", model=model_to_use, parsed=truncate(str(parsed), 500)
        )
        return parsed
