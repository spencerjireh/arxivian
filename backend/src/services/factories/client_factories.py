"""Factory functions for external API clients."""

from functools import lru_cache
from src.config import get_settings
from src.services.arxiv_client import ArxivClient
from src.services.embeddings_client import JinaEmbeddingsClient
from src.services.openai_client import OpenAIClient


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
    return JinaEmbeddingsClient(
        api_key=settings.jina_api_key, model="jina-embeddings-v3", dimension=1024
    )


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAIClient:
    """
    Create singleton OpenAI client.

    Returns:
        OpenAIClient instance
    """
    settings = get_settings()
    return OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
