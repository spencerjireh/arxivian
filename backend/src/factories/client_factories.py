"""Factory functions for external API clients."""

from functools import lru_cache
from typing import Optional

from src.config import get_settings
from src.clients.arxiv_client import ArxivClient
from src.clients.embeddings_client import JinaEmbeddingsClient
from src.clients.base_llm_client import BaseLLMClient
from src.clients.openai_client import OpenAIClient
from src.clients.zai_client import ZAIClient
from src.exceptions import ConfigurationError, InvalidModelError, InvalidProviderError


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
        raise InvalidProviderError(provider=provider, valid_providers=["openai", "zai"])

    # Use default model if not specified
    if model is None:
        model = settings.get_default_model(provider)

    # Validate model
    if not settings.validate_model(provider, model):
        allowed = settings.get_allowed_models(provider)
        raise InvalidModelError(model=model, provider=provider, valid_models=allowed)

    # Create appropriate client
    if provider == "openai":
        if not settings.openai_api_key:
            raise ConfigurationError(
                message="OpenAI API key not configured",
                details={"required_env_var": "OPENAI_API_KEY"},
            )
        openai_key: str = settings.openai_api_key
        return OpenAIClient(api_key=openai_key, model=model)
    elif provider == "zai":
        if not settings.zai_api_key:
            raise ConfigurationError(
                message="Z.AI API key not configured",
                details={"required_env_var": "ZAI_API_KEY"},
            )
        zai_key: str = settings.zai_api_key
        return ZAIClient(api_key=zai_key, model=model)

    raise InvalidProviderError(provider=provider, valid_providers=["openai", "zai"])


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
