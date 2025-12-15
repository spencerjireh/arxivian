"""Factory functions for external API clients."""

from functools import lru_cache
from typing import Optional

from src.config import get_settings
from src.clients.arxiv_client import ArxivClient
from src.clients.embeddings_client import JinaEmbeddingsClient
from src.clients.base_llm_client import BaseLLMClient
from src.clients.openai_client import OpenAIClient
from src.clients.zai_client import ZAIClient


@lru_cache(maxsize=1)
def get_arxiv_client() -> ArxivClient:
    """
    Create singleton arXiv client.

    Returns:
        ArxivClient instance
    """
    return ArxivClient()


@lru_cache(maxsize=1)
def get_embeddings_client() -> JinaEmbeddingsClient:
    """
    Create singleton Jina embeddings client.

    Returns:
        JinaEmbeddingsClient instance
    """
    settings = get_settings()
    return JinaEmbeddingsClient(api_key=settings.jina_api_key, model="jina-embeddings-v3")


def get_llm_client(provider: Optional[str] = None, model: Optional[str] = None) -> BaseLLMClient:
    """
    Create LLM client for specified provider and model.

    Args:
        provider: LLM provider ('openai' or 'zai'). Uses default if None.
        model: Model name. Uses provider's default if None.

    Returns:
        BaseLLMClient instance for the specified provider

    Raises:
        ValueError: If provider is invalid or model not allowed
    """
    settings = get_settings()

    # Use default provider if not specified
    if provider is None:
        provider = settings.default_llm_provider

    # Validate provider
    if provider not in ["openai", "zai"]:
        raise ValueError(f"Invalid provider '{provider}'. Must be 'openai' or 'zai'.")

    # Use default model if not specified
    if model is None:
        model = settings.get_default_model(provider)

    # Validate model
    if not settings.validate_model(provider, model):
        allowed = settings.get_allowed_models(provider)
        raise ValueError(
            f"Model '{model}' not allowed for provider '{provider}'. "
            f"Allowed models: {', '.join(allowed)}"
        )

    # Create appropriate client
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
            )
        openai_key: str = settings.openai_api_key
        return OpenAIClient(api_key=openai_key, model=model)
    elif provider == "zai":
        if not settings.zai_api_key:
            raise ValueError("Z.AI API key not configured. Set ZAI_API_KEY environment variable.")
        zai_key: str = settings.zai_api_key
        return ZAIClient(api_key=zai_key, model=model)

    raise ValueError(f"Provider '{provider}' not implemented")


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAIClient:
    """
    Create singleton OpenAI client (DEPRECATED).

    Use get_llm_client() instead.

    Returns:
        OpenAIClient instance
    """
    settings = get_settings()
    return OpenAIClient(api_key=settings.openai_api_key, model=settings.get_default_model("openai"))
