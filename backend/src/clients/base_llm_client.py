"""Abstract base class for LLM providers.

One implementation per provider, each talking to that vendor's own SDK rather than through a
normalising layer. The reason is feature fidelity: the point of reaching for a second
provider is usually something it does distinctively, and a translation layer flattens exactly
that. `clients/typesafe_client.py` already followed this pattern for Jev.

Messages are carried in the OpenAI shape (`ChatCompletionMessageParam`) because that is what
every caller already builds; a provider whose wire format differs converts on the way out.
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from src.exceptions import LLMTimeoutError

T = TypeVar("T", bound=BaseModel)

# Providers whose model strings are routed by the `provider/model` prefix.
OPENAI = "openai"
ANTHROPIC = "anthropic"


def provider_from_model(model: str) -> str:
    """Provider prefix of a `provider/model` string, defaulting to OpenAI when bare.

    The prefix convention predates the split into per-provider clients, so existing config
    values such as `openai/gpt-5-nano` keep working untouched.
    """
    return model.split("/", 1)[0] if "/" in model else OPENAI


def model_without_prefix(model: str) -> str:
    """The provider's own model id, with any `provider/` prefix stripped.

    Vendor SDKs want their bare id (`gpt-5-nano`), not the routed form.
    """
    return model.split("/", 1)[1] if "/" in model else model


class BaseLLMClient(ABC):
    """Abstract base class for LLM providers."""

    @asynccontextmanager
    async def _timeout(self, seconds: float):
        """Bound a call and report the timeout as ours, not the SDK's.

        Shared so both providers fail the same way: callers catch `LLMTimeoutError` and do not
        need to know which vendor's exception was underneath.
        """
        try:
            async with asyncio.timeout(seconds):
                yield
        except TimeoutError:
            raise LLMTimeoutError(provider=self.provider_name, timeout_seconds=seconds) from None

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
        yield ""  # pragma: no cover -- makes this a valid abstract async generator

    @abstractmethod
    async def generate_structured(
        self,
        messages: list[ChatCompletionMessageParam],
        response_format: type[T],
        model: str | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
    ) -> T:
        """Generate structured output using the provider's structured outputs API.

        `max_tokens` bounds the completion. None means "do not bound it", which is what
        batched callers need: a schema holding a list of N results has no fixed output
        size, and a cap sized for one result truncates the response into a parse failure
        (ARX-77). Anthropic requires the field, so it substitutes its own default there.
        """
        pass
