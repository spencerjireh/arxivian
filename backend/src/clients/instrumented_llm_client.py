"""Instrumented LLM client wrapper for metrics collection.

This wrapper provides a hook for collecting metrics (latency, errors, future token counts)
without coupling to any specific observability backend. Tracing is handled separately
by the LangGraph CallbackHandler.
"""

import time
from typing import AsyncIterator, List, Optional, Type, TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from src.clients.base_llm_client import BaseLLMClient
from src.utils.logger import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class InstrumentedLLMClient(BaseLLMClient):
    """
    Wrapper that adds metrics collection to any BaseLLMClient.

    Currently logs:
    - Latency per call
    - Errors with context

    Future extensions:
    - Token usage tracking
    - Cost calculation
    - Prometheus metrics
    - Rate limit tracking
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
        """Generate completion with metrics collection."""
        start = time.perf_counter()
        model_name = model or self.model

        try:
            result = await self._client.generate_completion(
                messages, model, temperature, max_tokens, stream, timeout
            )

            if stream:
                # For streaming, wrap the iterator to log after completion
                return self._instrumented_stream(result, model_name, start)  # type: ignore[arg-type]
            else:
                latency_ms = (time.perf_counter() - start) * 1000
                log.debug(
                    "llm_completion",
                    provider=self.provider_name,
                    model=model_name,
                    latency_ms=round(latency_ms, 2),
                )
                return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log.warning(
                "llm_error",
                provider=self.provider_name,
                model=model_name,
                error=str(e),
                latency_ms=round(latency_ms, 2),
            )
            raise

    async def _instrumented_stream(
        self,
        stream: AsyncIterator[str],
        model: str,
        start: float,
    ) -> AsyncIterator[str]:
        """Wrap streaming response to collect metrics after completion."""
        token_count = 0
        try:
            async for token in stream:
                token_count += 1
                yield token

            latency_ms = (time.perf_counter() - start) * 1000
            log.debug(
                "llm_streaming",
                provider=self.provider_name,
                model=model,
                tokens=token_count,
                latency_ms=round(latency_ms, 2),
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log.warning(
                "llm_stream_error",
                provider=self.provider_name,
                model=model,
                tokens=token_count,
                error=str(e),
                latency_ms=round(latency_ms, 2),
            )
            raise

    async def generate_structured(
        self,
        messages: List[ChatCompletionMessageParam],
        response_format: Type[T],
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> T:
        """Generate structured output with metrics collection."""
        start = time.perf_counter()
        model_name = model or self.model

        try:
            result = await self._client.generate_structured(
                messages, response_format, model, timeout
            )

            latency_ms = (time.perf_counter() - start) * 1000
            log.debug(
                "llm_structured",
                provider=self.provider_name,
                model=model_name,
                response_format=response_format.__name__,
                latency_ms=round(latency_ms, 2),
            )
            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log.warning(
                "llm_error",
                provider=self.provider_name,
                model=model_name,
                response_format=response_format.__name__,
                error=str(e),
                latency_ms=round(latency_ms, 2),
            )
            raise
