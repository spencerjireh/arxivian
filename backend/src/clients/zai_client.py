"""Z.AI API client using OpenAI-compatible interface."""

from typing import List, AsyncIterator, Type, Optional, Any, cast
from pydantic import BaseModel
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.clients.base_llm_client import BaseLLMClient


class ZAIClient(BaseLLMClient):
    """Client for Z.AI API with OpenAI-compatible interface."""

    def __init__(self, api_key: str, model: str = "glm-4.6"):
        """
        Initialize Z.AI client.

        Args:
            api_key: Z.AI API key
            model: Default model to use
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.z.ai/api/paas/v4/")
        self._model = model

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "zai"

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
    ) -> str | AsyncIterator[str]:
        """
        Generate completion from Z.AI.

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
                messages=cast(Any, messages),
                model=model_to_use,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=cast(Any, messages),
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""

    async def _generate_streaming(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Generate streaming completion."""
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

    async def generate_structured(
        self,
        messages: List[ChatCompletionMessageParam],
        response_format: Type[BaseModel],
        model: Optional[str] = None,
    ) -> BaseModel:
        """
        Generate structured output using Z.AI.

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
            messages=cast(Any, messages),
            response_format=response_format,
        )

        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Failed to parse response")
        return parsed
