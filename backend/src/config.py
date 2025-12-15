"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List, Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    postgres_url: str = "postgresql+asyncpg://user:password@localhost:5432/arxiv_rag"

    # LLM Provider Configuration
    default_llm_provider: Literal["openai", "zai"] = "openai"

    # OpenAI Configuration
    openai_api_key: str
    openai_allowed_models: str = "gpt-4o-mini,gpt-4o,gpt-4-turbo"

    # Z.AI Configuration
    zai_api_key: Optional[str] = None
    zai_allowed_models: str = "glm-4.6,glm-4.5,glm-4-32b-0414-128k"

    # Embeddings
    jina_api_key: str

    # Search configuration
    default_top_k: int = 3
    rrf_k: int = 60

    # Chunking configuration
    chunk_size_words: int = 600
    chunk_overlap_words: int = 100
    min_chunk_words: int = 100

    # Agent Configuration
    guardrail_threshold: int = 75
    max_retrieval_attempts: int = 3

    # App
    debug: bool = False
    log_level: str = "INFO"

    # Helper methods
    def get_allowed_models(self, provider: str) -> List[str]:
        """Get list of allowed models for a provider."""
        if provider == "openai":
            return [m.strip() for m in self.openai_allowed_models.split(",")]
        elif provider == "zai":
            return [m.strip() for m in self.zai_allowed_models.split(",")]
        else:
            return []

    def get_default_model(self, provider: str) -> str:
        """Get default model for a provider (first in allowed list)."""
        models = self.get_allowed_models(provider)
        if not models:
            raise ValueError(f"No models configured for provider: {provider}")
        return models[0]

    def validate_model(self, provider: str, model: str) -> bool:
        """Check if model is allowed for provider."""
        return model in self.get_allowed_models(provider)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
