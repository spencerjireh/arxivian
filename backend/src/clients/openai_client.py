"""OpenAI chat client, on the vendor SDK.

Replaces the LiteLLM path (ARX-75). Messages already arrive in the OpenAI shape, so this is
the thin half of the two providers: no conversion, and structured output is native via
`chat.completions.parse`, which validates into the Pydantic model for us instead of us
parsing JSON out of a text field.

Timeout handling lives on `BaseLLMClient._timeout`, so a slow call raises `LLMTimeoutError`
here exactly as it does for Anthropic.
"""

from collections.abc import AsyncIterator
from typing import TypeVar

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from src.clients.base_llm_client import OPENAI, BaseLLMClient, model_without_prefix
from src.utils.logger import get_logger, truncate

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_MAX_TOKENS = 4096

# Models that reject a non-default `temperature`, learned at runtime. The reasoning models do:
# `gpt-5-nano` answers `temperature=0.3` with a 400 ("Only the default (1) value is
# supported"). LiteLLM hid this behind `drop_params = True`, so production has in fact never
# applied a temperature to OpenAI; dropping it here keeps that behaviour rather than starting
# to fail every call. Learned rather than hardcoded so a model list cannot go stale.
_NO_TEMPERATURE: set[str] = set()


def _rejects_temperature(exc: openai.BadRequestError) -> bool:
    """True when a 400 is specifically about the `temperature` parameter."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("param") == "temperature":
            return True
    return "temperature" in str(exc) and "does not support" in str(exc)


class OpenAIClient(BaseLLMClient):
    """Chat, streaming and structured output against the OpenAI API."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-5-nano",
        timeout: float = 60.0,
        structured_output_model: str | None = None,
    ):
        self._model = model
        self.default_timeout = timeout
        self._structured_output_model = structured_output_model
        # `max_retries=0`: retries are the caller's business. The scoring and triage tasks
        # own their own retry and timeout budgets, and a silent SDK retry inside a bounded
        # task burns that budget without telling anyone.
        self._client = AsyncOpenAI(api_key=api_key, max_retries=0)

    async def _create(self, *, model: str, temperature: float, **kwargs: object):
        """Create a completion, dropping `temperature` for models that reject it.

        The first rejection per model is remembered, so this costs one extra round trip once
        per process per model rather than on every call.
        """
        if model not in _NO_TEMPERATURE:
            try:
                return await self._client.chat.completions.create(
                    model=model, temperature=temperature, **kwargs
                )
            except openai.BadRequestError as exc:
                if not _rejects_temperature(exc):
                    raise
                log.info("openai dropping unsupported temperature", model=model)
                _NO_TEMPERATURE.add(model)
        return await self._client.chat.completions.create(model=model, **kwargs)

    @property
    def provider_name(self) -> str:
        return OPENAI

    @property
    def model(self) -> str:
        return self._model

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

        log.debug(
            "openai request",
            model=model_to_use,
            messages=len(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=effective_timeout,
        )

        async with self._timeout(effective_timeout):
            response = await self._create(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )

        content = response.choices[0].message.content or ""
        usage = response.usage

        log.debug(
            "openai response",
            model=model_to_use,
            content=truncate(content, 2000),
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
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

        log.debug(
            "openai stream request",
            model=model_to_use,
            messages=len(messages),
            timeout=effective_timeout,
        )

        # The timeout spans the whole stream, not just the first token: a stalled generation
        # halfway through is the failure that strands a chat turn.
        async with self._timeout(effective_timeout):
            stream = await self._create(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

    async def generate_structured(
        self,
        messages: list[ChatCompletionMessageParam],
        response_format: type[T],
        model: str | None = None,
        timeout: float | None = None,
    ) -> T:
        model_to_use = model_without_prefix(model or self._structured_output_model or self._model)
        effective_timeout = timeout if timeout is not None else self.default_timeout

        log.debug(
            "openai structured request",
            model=model_to_use,
            response_format=response_format.__name__,
            timeout=effective_timeout,
        )

        async with self._timeout(effective_timeout):
            completion = await self._client.chat.completions.parse(
                model=model_to_use,
                messages=messages,
                response_format=response_format,
                max_completion_tokens=DEFAULT_MAX_TOKENS,
            )

        parsed = completion.choices[0].message.parsed
        if parsed is None:
            # A refusal or a length-truncated response both land here. Callers treat this as
            # a failed batch rather than as empty data, which matters for triage: a silently
            # empty verdict set would read as "nothing qualified".
            refusal = completion.choices[0].message.refusal
            raise ValueError(f"Structured output returned no parsed object (refusal={refusal})")

        log.debug(
            "openai structured response", model=model_to_use, parsed=truncate(str(parsed), 500)
        )
        return parsed
