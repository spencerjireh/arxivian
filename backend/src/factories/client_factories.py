"""Factory functions for external API clients."""

from functools import lru_cache

from src.config import Settings, get_settings
from src.clients.arxiv_client import ArxivClient
from src.clients.embeddings_client import JinaEmbeddingsClient
from src.clients.base_llm_client import BaseLLMClient
from src.clients.litellm_client import LiteLLMClient
from src.exceptions import InvalidModelError


def _validate_model(model: str, settings: Settings) -> None:
    """Raise InvalidModelError if model is not in the allowed list."""
    if not settings.is_model_allowed(model):
        allowed = settings.get_allowed_models_list()
        provider = model.split("/", 1)[0] if "/" in model else "unknown"
        raise InvalidModelError(model=model, provider=provider, valid_models=allowed)


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


def get_llm_client(model: str | None = None) -> BaseLLMClient:
    """
    Create LLM client for specified LiteLLM model.

    Args:
        model: LiteLLM-format model string (e.g. "openai/gpt-4o-mini").
               Uses default_llm_model from settings if None.

    Returns:
        BaseLLMClient instance

    Raises:
        InvalidModelError: If model is not in the allowed list
    """
    settings = get_settings()

    if model is None:
        model = settings.default_llm_model

    _validate_model(model, settings)

    structured_model = settings.structured_output_model or None
    if structured_model:
        _validate_model(structured_model, settings)

    return LiteLLMClient(
        model=model,
        timeout=float(settings.llm_call_timeout_seconds),
        structured_output_model=structured_model,
    )
