"""Provider-agnostic LLM tracing wrapper for Langfuse."""

from typing import AsyncIterator, List, Optional, Type, TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from src.clients.base_llm_client import BaseLLMClient
from src.utils.logger import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

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
        """Trace non-streaming completion."""
        generation = langfuse.generation(
            name=f"{self.provider_name}_completion",
            model=model,
            input=messages,
            metadata={"temperature": temperature, "max_tokens": max_tokens},
        )

        try:
            result = await self._client.generate_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                timeout=timeout,
            )
            # Result is str when stream=False
            generation.end(output=result)
            return result  # type: ignore[return-value]

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
        """Trace streaming completion - collects tokens and logs at end."""
        generation = langfuse.generation(
            name=f"{self.provider_name}_streaming",
            model=model,
            input=messages,
            metadata={"temperature": temperature, "stream": True},
        )

        collected: list[str] = []
        try:
            stream = await self._client.generate_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                timeout=timeout,
            )

            # Stream is AsyncIterator[str] when stream=True
            async for token in stream:  # type: ignore[union-attr]
                collected.append(token)
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
        """Generate structured output with automatic Langfuse tracing."""
        langfuse = _get_langfuse()
        model_name = model or self.model

        if not langfuse:
            return await self._client.generate_structured(messages, response_format, model, timeout)

        generation = langfuse.generation(
            name=f"{self.provider_name}_structured",
            model=model_name,
            input=messages,
            metadata={"response_format": response_format.__name__},
        )

        try:
            result = await self._client.generate_structured(
                messages, response_format, model, timeout
            )
            generation.end(output=result.model_dump())
            return result

        except Exception as e:
            generation.end(level="ERROR", status_message=str(e))
            raise
