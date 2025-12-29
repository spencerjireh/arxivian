"""OpenAI API client for LLM generation and reasoning."""

import asyncio
from typing import List, AsyncIterator, Type, Optional, Any, cast, TypeVar

from httpx import Timeout
from pydantic import BaseModel
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.clients.base_llm_client import BaseLLMClient
from src.exceptions import LLMTimeoutError
from src.utils.logger import get_logger, truncate

T = TypeVar("T", bound=BaseModel)

log = get_logger(__name__)


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI API with support for completion and structured outputs."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout: float = 60.0):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Default model to use
            timeout: Default timeout in seconds for LLM calls
        """
        self.default_timeout = timeout
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=Timeout(timeout, connect=10.0),
        )
        self._model = model

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "openai"

    @property
    def model(self) -> str:
        """Return current model name."""
        return self._model

    async def generate_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        stream: bool = False,
        timeout: Optional[float] = None,
    ) -> str | AsyncIterator[str]:
        """
        Generate completion from OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (overrides default)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            timeout: Optional timeout in seconds (uses client default if None)

        Returns:
            str if stream=False, AsyncIterator[str] if stream=True
        """
        model_to_use = model or self.model
        effective_timeout = timeout if timeout is not None else self.default_timeout

        # Log full prompt at debug level
        for msg in messages:
            content = msg.get("content", "")
            log.debug(
                "llm prompt message",
                role=msg.get("role"),
                content=truncate(str(content), 2000),
            )

        log.debug(
            "openai request",
            model=model_to_use,
            messages=len(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            timeout=effective_timeout,
        )

        if stream:
            return self._generate_streaming(
                messages=cast(Any, messages),
                model=model_to_use,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=effective_timeout,
            )
        else:
            try:
                async with asyncio.timeout(effective_timeout):
                    response = await self.client.chat.completions.create(
                        model=model_to_use,
                        messages=cast(Any, messages),
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
            except asyncio.TimeoutError:
                log.error("openai timeout", model=model_to_use, timeout=effective_timeout)
                raise LLMTimeoutError(provider="openai", timeout_seconds=effective_timeout)

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

    async def _generate_streaming(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> AsyncIterator[str]:
        """Generate streaming completion."""
        try:
            async with asyncio.timeout(timeout):
                stream = await self.client.chat.completions.create(
                    model=model,
                    messages=cast(Any, messages),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        except asyncio.TimeoutError:
            log.error("openai streaming timeout", model=model, timeout=timeout)
            raise LLMTimeoutError(provider="openai", timeout_seconds=timeout)

    async def generate_structured(
        self,
        messages: List[ChatCompletionMessageParam],
        response_format: Type[T],
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> T:
        """
        Generate structured output using OpenAI's structured outputs.

        Args:
            messages: List of message dicts
            response_format: Pydantic model class for response schema
            model: Model to use (overrides default)
            timeout: Optional timeout in seconds (uses client default if None)

        Returns:
            Instance of response_format Pydantic model
        """
        model_to_use = model or self.model
        effective_timeout = timeout if timeout is not None else self.default_timeout

        log.debug(
            "openai structured request",
            model=model_to_use,
            response_format=response_format.__name__,
            timeout=effective_timeout,
        )

        try:
            async with asyncio.timeout(effective_timeout):
                response = await self.client.beta.chat.completions.parse(
                    model=model_to_use,
                    messages=cast(Any, messages),
                    response_format=response_format,
                )
        except asyncio.TimeoutError:
            log.error("openai structured timeout", model=model_to_use, timeout=effective_timeout)
            raise LLMTimeoutError(provider="openai", timeout_seconds=effective_timeout)

        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Failed to parse response")

        log.debug("openai structured response", parsed=str(parsed)[:500])

        return parsed
