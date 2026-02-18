"""LiteLLM-based LLM client with unified multi-provider support.

Routes to any LiteLLM-supported provider via model prefix (e.g. openai/gpt-4o-mini,
nvidia_nim/meta/llama-3.1-8b-instruct). Langfuse tracing is handled via LiteLLM's
global callback system configured at startup in main.py.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, TypeVar

import litellm
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from src.clients.base_llm_client import BaseLLMClient
from src.clients.langfuse_utils import get_trace_context
from src.exceptions import LLMTimeoutError
from src.utils.logger import get_logger, truncate

T = TypeVar("T", bound=BaseModel)

log = get_logger(__name__)

# Providers that support native Pydantic response_format (schema-constrained decoding).
# All others fall back to prompt-based structured output with JSON mode.
NATIVE_STRUCTURED_OUTPUT_PROVIDERS: frozenset[str] = frozenset({"openai", "anthropic", "google"})


def _provider_from_model(model: str) -> str:
    """Extract provider prefix from a LiteLLM model string."""
    return model.split("/", 1)[0] if "/" in model else "openai"


def _inject_schema(
    messages: list[ChatCompletionMessageParam],
    response_format: type[BaseModel],
) -> list[dict[str, Any]]:
    """Append JSON schema instructions to the system message for prompt-based structured output."""
    schema = json.dumps(response_format.model_json_schema(), indent=2)
    suffix = (
        "\n\nRespond with a single valid JSON object matching this exact schema:\n"
        f"{schema}\n"
        "Output ONLY the JSON object. No markdown fences, no explanation."
    )
    patched: list[dict[str, Any]] = []
    injected = False
    for msg in messages:
        if msg.get("role") == "system" and not injected:  # type: ignore[union-attr]
            content = msg["content"]  # type: ignore[index]
            if not isinstance(content, str):
                raise TypeError(
                    f"Schema injection requires string system message, got {type(content)}"
                )
            patched.append({**msg, "content": content + suffix})
            injected = True
        else:
            patched.append(dict(msg))  # type: ignore[arg-type]
    if not injected:
        patched.insert(0, {"role": "system", "content": suffix.lstrip()})
    return patched


class LiteLLMClient(BaseLLMClient):
    """Unified LLM client backed by LiteLLM.

    Supports any provider that LiteLLM handles via model prefix routing.
    """

    def __init__(
        self,
        model: str = "nvidia_nim/openai/gpt-oss-120b",
        timeout: float = 60.0,
        structured_output_model: str | None = None,
    ):
        self._model = model
        self.default_timeout = timeout
        self._structured_output_model = structured_output_model

    @property
    def provider_name(self) -> str:
        return _provider_from_model(self._model)

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
        model_to_use = model or self._structured_output_model or self._model
        effective_timeout = timeout if timeout is not None else self.default_timeout
        metadata = self._build_metadata()
        provider = _provider_from_model(model_to_use)
        native = provider in NATIVE_STRUCTURED_OUTPUT_PROVIDERS

        log.debug(
            "litellm structured request",
            model=model_to_use,
            response_format=response_format.__name__,
            native_structured=native,
            timeout=effective_timeout,
        )

        call_kwargs: dict[str, Any] = {
            "model": model_to_use,
            "metadata": metadata,
        }
        if native:
            call_kwargs["messages"] = messages
            call_kwargs["response_format"] = response_format
        else:
            call_kwargs["messages"] = _inject_schema(messages, response_format)
            call_kwargs["response_format"] = {"type": "json_object"}

        async with self._timeout(effective_timeout):
            response = await litellm.acompletion(**call_kwargs)  # type: ignore[arg-type]

        content = response.choices[0].message.content  # type: ignore[union-attr]
        if content is None:
            raise ValueError("Failed to parse response: empty content")

        parsed = response_format.model_validate_json(content)

        log.debug(
            "litellm structured response", model=model_to_use, parsed=truncate(str(parsed), 500)
        )

        return parsed
