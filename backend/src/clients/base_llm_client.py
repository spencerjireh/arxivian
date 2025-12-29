"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import List, AsyncIterator, Type, Optional, TypeVar
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam

T = TypeVar("T", bound=BaseModel)


class BaseLLMClient(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name (e.g., 'openai', 'zai')."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Return current model name."""
        pass

    @abstractmethod
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
        Generate completion from LLM.

        Args:
            messages: List of chat completion messages
            model: Model to use (overrides default)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            timeout: Optional timeout in seconds (uses client default if None)

        Returns:
            str if stream=False, AsyncIterator[str] if stream=True
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        messages: List[ChatCompletionMessageParam],
        response_format: Type[T],
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> T:
        """
        Generate structured output using provider's structured outputs API.

        Args:
            messages: List of chat completion messages
            response_format: Pydantic model class for response schema
            model: Model to use (overrides default)
            timeout: Optional timeout in seconds (uses client default if None)

        Returns:
            Instance of response_format Pydantic model
        """
        pass
