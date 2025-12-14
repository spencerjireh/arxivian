"""OpenAI API client for LLM generation and reasoning."""

from typing import List, AsyncIterator, Type, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI


class OpenAIClient:
    """Client for OpenAI API with support for completion and structured outputs."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Default model to use
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_completion(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """
        Generate completion from OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (overrides default)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            str if stream=False, AsyncIterator[str] if stream=True
        """
        model_to_use = model or self.model

        if stream:
            return self._generate_streaming(
                messages=messages,
                model=model_to_use,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

    async def _generate_streaming(
        self,
        messages: List[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Generate streaming completion."""
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_structured(
        self,
        messages: List[dict],
        response_format: Type[BaseModel],
        model: Optional[str] = None,
    ) -> BaseModel:
        """
        Generate structured output using OpenAI's structured outputs.

        Args:
            messages: List of message dicts
            response_format: Pydantic model class for response schema
            model: Model to use (overrides default)

        Returns:
            Instance of response_format Pydantic model
        """
        model_to_use = model or self.model

        response = await self.client.beta.chat.completions.parse(
            model=model_to_use,
            messages=messages,
            response_format=response_format,
        )

        return response.choices[0].message.parsed
