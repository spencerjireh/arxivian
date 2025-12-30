"""Provider-agnostic LLM tracing wrapper for Langfuse.

This module provides tracing for LLM calls that integrates with the
LangGraph CallbackHandler trace hierarchy. Use set_trace_context() to
establish a parent trace before executing LLM calls.
"""

from contextvars import ContextVar
from typing import AsyncIterator, List, Optional, Type, TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from src.clients.base_llm_client import BaseLLMClient
from src.utils.logger import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# Context variable for trace hierarchy - allows LLM calls to nest under the graph trace
_current_trace_id: ContextVar[str | None] = ContextVar("langfuse_trace_id", default=None)


def set_trace_context(trace_id: str | None) -> None:
    """Set the current Langfuse trace ID for nested LLM call tracing.

    Call this before executing LLM operations to ensure generations
    are nested under the parent trace (e.g., from LangGraph CallbackHandler).

    Args:
        trace_id: The parent trace ID, or None to clear context.
    """
    _current_trace_id.set(trace_id)


def get_trace_context() -> str | None:
    """Get the current Langfuse trace ID.

    Returns:
        The current trace ID if set, None otherwise.
    """
    return _current_trace_id.get()


# Lazy Langfuse initialization
_langfuse_client = None
LANGFUSE_AVAILABLE = False

try:
    from langfuse import Langfuse

    LANGFUSE_AVAILABLE = True
except ImportError:
    Langfuse = None  # type: ignore[misc, assignment]


def _get_langfuse() -> Optional["Langfuse"]:  # type: ignore[name-defined]
    """Get or create singleton Langfuse client."""
    global _langfuse_client
    if not LANGFUSE_AVAILABLE:
        return None
    if _langfuse_client is None:
        from src.config import get_settings

        settings = get_settings()
        if settings.langfuse_enabled:
            if not settings.langfuse_public_key or not settings.langfuse_secret_key:
                log.warning(
                    "langfuse_keys_missing",
                    message="Langfuse is enabled but API keys are not configured. Tracing disabled.",
                )
                return None
            _langfuse_client = Langfuse(  # type: ignore[misc]
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            log.info("langfuse_client_initialized")
    return _langfuse_client


def shutdown_langfuse() -> None:
    """Flush and shutdown singleton Langfuse client.

    Call this during application shutdown to ensure all pending
    events are sent before the process exits.
    """
    global _langfuse_client
    if _langfuse_client is not None:
        _langfuse_client.flush()
        _langfuse_client.shutdown()
        _langfuse_client = None
        log.info("langfuse_shutdown")


class TracedLLMClient(BaseLLMClient):
    """
    Wrapper that adds Langfuse tracing to any BaseLLMClient.

    Automatically traces:
    - Non-streaming completions (full input/output)
    - Streaming completions (collects tokens, logs complete response)
    - Structured outputs (input/parsed output)

    Usage:
        base_client = OpenAIClient(...)
        traced_client = TracedLLMClient(base_client)
        # Use traced_client exactly like base_client
    """

    def __init__(self, client: BaseLLMClient):
        self._client = client

    @property
    def provider_name(self) -> str:
        return self._client.provider_name

    @property
    def model(self) -> str:
        return self._client.model

    async def generate_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        stream: bool = False,
        timeout: Optional[float] = None,
    ) -> str | AsyncIterator[str]:
        """Generate completion with automatic Langfuse tracing."""
        langfuse = _get_langfuse()
        model_name = model or self.model

        if not langfuse:
            return await self._client.generate_completion(
                messages, model, temperature, max_tokens, stream, timeout
            )

        if stream:
            return self._traced_stream(
                messages, model_name, temperature, max_tokens, timeout, langfuse
            )
        else:
            return await self._traced_completion(
                messages, model_name, temperature, max_tokens, timeout, langfuse
            )

    async def _traced_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: Optional[float],
        langfuse: "Langfuse",  # type: ignore[name-defined]
    ) -> str:
        """Trace non-streaming completion, nested under parent trace if context set."""
        trace_id = get_trace_context()
        gen_name = f"{self.provider_name}_completion"
        metadata = {"temperature": temperature, "max_tokens": max_tokens}

        async def _call() -> str:
            result = await self._client.generate_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                timeout=timeout,
            )
            return result  # type: ignore[return-value]

        if trace_id:
            # Nest under parent trace from CallbackHandler
            with langfuse.start_as_current_observation(
                as_type="generation",
                name=gen_name,
                trace_context={"trace_id": trace_id},
            ) as generation:
                generation.update(model=model, input=messages, metadata=metadata)
                try:
                    result = await _call()
                    generation.update(output=result)
                    return result
                except Exception as e:
                    generation.update(level="ERROR", status_message=str(e))
                    raise
        else:
            # Fallback: top-level trace (backwards compatible)
            generation = langfuse.generation(
                name=gen_name, model=model, input=messages, metadata=metadata
            )
            try:
                result = await _call()
                generation.end(output=result)
                return result
            except Exception as e:
                generation.end(level="ERROR", status_message=str(e))
                raise

    async def _traced_stream(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: Optional[float],
        langfuse: "Langfuse",  # type: ignore[name-defined]
    ) -> AsyncIterator[str]:
        """Trace streaming completion, nested under parent trace if context set."""
        trace_id = get_trace_context()
        gen_name = f"{self.provider_name}_streaming"
        metadata = {"temperature": temperature, "stream": True}

        collected: list[str] = []

        async def _stream() -> AsyncIterator[str]:
            stream = await self._client.generate_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                timeout=timeout,
            )
            async for token in stream:  # type: ignore[union-attr]
                collected.append(token)
                yield token

        if trace_id:
            with langfuse.start_as_current_observation(
                as_type="generation",
                name=gen_name,
                trace_context={"trace_id": trace_id},
            ) as generation:
                generation.update(model=model, input=messages, metadata=metadata)
                try:
                    async for token in _stream():
                        yield token
                    generation.update(output="".join(collected))
                except Exception as e:
                    generation.update(
                        output="".join(collected) if collected else None,
                        level="ERROR",
                        status_message=str(e),
                    )
                    raise
        else:
            generation = langfuse.generation(
                name=gen_name, model=model, input=messages, metadata=metadata
            )
            try:
                async for token in _stream():
                    yield token
                generation.end(output="".join(collected))
            except Exception as e:
                generation.end(
                    output="".join(collected) if collected else None,
                    level="ERROR",
                    status_message=str(e),
                )
                raise

    async def generate_structured(
        self,
        messages: List[ChatCompletionMessageParam],
        response_format: Type[T],
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> T:
        """Generate structured output, nested under parent trace if context set."""
        langfuse = _get_langfuse()
        model_name = model or self.model

        if not langfuse:
            return await self._client.generate_structured(messages, response_format, model, timeout)

        trace_id = get_trace_context()
        gen_name = f"{self.provider_name}_structured"
        metadata = {"response_format": response_format.__name__}

        async def _call() -> T:
            return await self._client.generate_structured(messages, response_format, model, timeout)

        if trace_id:
            with langfuse.start_as_current_observation(
                as_type="generation",
                name=gen_name,
                trace_context={"trace_id": trace_id},
            ) as generation:
                generation.update(model=model_name, input=messages, metadata=metadata)
                try:
                    result = await _call()
                    generation.update(output=result.model_dump())
                    return result
                except Exception as e:
                    generation.update(level="ERROR", status_message=str(e))
                    raise
        else:
            generation = langfuse.generation(
                name=gen_name, model=model_name, input=messages, metadata=metadata
            )
            try:
                result = await _call()
                generation.end(output=result.model_dump())
                return result
            except Exception as e:
                generation.end(level="ERROR", status_message=str(e))
                raise
