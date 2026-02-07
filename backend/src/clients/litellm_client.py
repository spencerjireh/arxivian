"""LiteLLM-based LLM client with unified multi-provider support.

Routes to any LiteLLM-supported provider via model prefix (e.g. openai/gpt-4o-mini,
nvidia_nim/meta/llama-3.1-8b-instruct). Langfuse tracing is handled via LiteLLM's
global callback system configured at startup in main.py.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypeVar

import litellm
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from src.clients.base_llm_client import BaseLLMClient
from src.clients.langfuse_utils import get_trace_context
from src.exceptions import LLMTimeoutError
from src.utils.logger import get_logger, truncate

T = TypeVar("T", bound=BaseModel)

log = get_logger(__name__)


class LiteLLMClient(BaseLLMClient):
    """Unified LLM client backed by LiteLLM.

    Supports any provider that LiteLLM handles via model prefix routing.
    """

    def __init__(self, model: str = "openai/gpt-4o-mini", timeout: float = 60.0):
        self._model = model
        self.default_timeout = timeout

    @property
    def provider_name(self) -> str:
        if "/" in self._model:
            return self._model.split("/", 1)[0]
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def _build_metadata(self) -> dict:
        """Build per-call metadata with trace context for Langfuse nesting."""
        metadata: dict = {}
        trace_id = get_trace_context()
        if trace_id:
            metadata["existing_trace_id"] = trace_id
        return metadata

    @asynccontextmanager
    async def _timeout(self, seconds: float):
        try:
            async with asyncio.timeout(seconds):
                yield
        except asyncio.TimeoutError:
            raise LLMTimeoutError(provider=self.provider_name, timeout_seconds=seconds)

    async def generate_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        timeout: float | None = None,
    ) -> str:
        model_to_use = model or self._model
        effective_timeout = timeout if timeout is not None else self.default_timeout
        metadata = self._build_metadata()

        log.debug(
            "litellm request",
            model=model_to_use,
            messages=len(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=effective_timeout,
        )

        async with self._timeout(effective_timeout):
            response = await litellm.acompletion(
                model=model_to_use,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                metadata=metadata,
            )

        content = response.choices[0].message.content or ""  # type: ignore[union-attr]
        usage = response.usage  # type: ignore[union-attr]

        log.debug(
            "litellm response",
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
        model_to_use = model or self._model
        effective_timeout = timeout if timeout is not None else self.default_timeout
        metadata = self._build_metadata()

        log.debug(
            "litellm stream request",
            model=model_to_use,
            messages=len(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=effective_timeout,
        )

        async with self._timeout(effective_timeout):
            response = await litellm.acompletion(
                model=model_to_use,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                metadata=metadata,
            )

            async for chunk in response:  # type: ignore[union-attr]
                delta = chunk.choices[0].delta  # type: ignore[union-attr]
                if delta and delta.content:
                    yield delta.content

    async def generate_structured(
        self,
        messages: list[ChatCompletionMessageParam],
        response_format: type[T],
        model: str | None = None,
        timeout: float | None = None,
    ) -> T:
        model_to_use = model or self._model
        effective_timeout = timeout if timeout is not None else self.default_timeout
        metadata = self._build_metadata()

        log.debug(
            "litellm structured request",
            model=model_to_use,
            response_format=response_format.__name__,
            timeout=effective_timeout,
        )

        async with self._timeout(effective_timeout):
            response = await litellm.acompletion(
                model=model_to_use,
                messages=messages,  # type: ignore[arg-type]
                response_format=response_format,
                metadata=metadata,
            )

        content = response.choices[0].message.content  # type: ignore[union-attr]
        if content is None:
            raise ValueError("Failed to parse response: empty content")

        parsed = response_format.model_validate_json(content)

        log.debug("litellm structured response", parsed=str(parsed)[:500])

        return parsed
