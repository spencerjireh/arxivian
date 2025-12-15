"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import List, AsyncIterator, Type, Optional
from pydantic import BaseModel


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
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """
        Generate completion from LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (overrides default)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            str if stream=False, AsyncIterator[str] if stream=True
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        messages: List[dict],
        response_format: Type[BaseModel],
        model: Optional[str] = None,
    ) -> BaseModel:
        """
        Generate structured output using provider's structured outputs API.

        Args:
            messages: List of message dicts
            response_format: Pydantic model class for response schema
            model: Model to use (overrides default)

        Returns:
            Instance of response_format Pydantic model
        """
        pass
