"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMClient(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name (e.g., 'openai', 'nvidia_nim')."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Return current model name."""
        pass

    @abstractmethod
    async def generate_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        timeout: float | None = None,
    ) -> str:
        """Generate a non-streaming completion from the LLM."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[ChatCompletionMessageParam],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        timeout: float | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming completion from the LLM."""
        pass
        yield  # pragma: no cover -- makes this a valid abstract async generator

    @abstractmethod
    async def generate_structured(
        self,
        messages: list[ChatCompletionMessageParam],
        response_format: type[T],
        model: str | None = None,
        timeout: float | None = None,
    ) -> T:
        """Generate structured output using the provider's structured outputs API."""
        pass
