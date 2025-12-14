"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    # Database
    postgres_url: str = "postgresql+asyncpg://user:password@localhost:5432/arxiv_rag"

    # External APIs
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    jina_api_key: str

    # Search configuration
    default_top_k: int = 3
    rrf_k: int = 60

    # Chunking configuration
    chunk_size_words: int = 600
    chunk_overlap_words: int = 100
    min_chunk_words: int = 100

    # Agentic RAG
    guardrail_threshold: int = 75
    max_retrieval_attempts: int = 3

    # Langfuse (optional)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_enabled: bool = False

    # App
    debug: bool = False
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
