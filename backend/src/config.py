"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    postgres_url: str = "postgresql+asyncpg://user:password@localhost:5432/arxiv_rag"

    # LLM Configuration (LiteLLM-format model strings: "provider/model")
    default_llm_model: str = "openai/gpt-5-nano"
    allowed_llm_models: str = "openai/gpt-5-nano,openai/gpt-4o-mini"

    # Provider API Keys
    openai_api_key: str = ""
    nvidia_nim_api_key: Optional[str] = None
    nvidia_nim_api_base: Optional[str] = None

    # Embeddings
    jina_api_key: str = ""

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
    default_max_iterations: int = 5

    # Request Lifecycle Configuration
    agent_timeout_seconds: int = 180  # 3 minutes max per request
    llm_call_timeout_seconds: int = 60  # 1 minute per LLM call

    # Redis (separate DB from Celery)
    redis_url: str = "redis://redis:6379/2"

    # App
    debug: bool = False
    log_level: str = "INFO"
    log_request_body: bool = True
    log_response_body: bool = True

    # Langfuse Observability
    langfuse_enabled: bool = False
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "http://langfuse:3000"  # Self-hosted default

    # Clerk Authentication
    clerk_secret_key: str = ""

    # Celery/Redis
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    celery_task_timeout: int = 600  # 10 minutes

    # API Authentication
    api_key: str = ""

    # Scheduled jobs
    ingest_schedule_cron: str = "0 2 * * *"  # Daily at 2am UTC
    cleanup_schedule_cron: str = "0 3 * * *"  # Daily at 3am UTC
    cleanup_retention_days: int = 90

    # Helper methods
    def get_allowed_models_list(self) -> List[str]:
        """Get list of all allowed LiteLLM model strings."""
        return [m.strip() for m in self.allowed_llm_models.split(",") if m.strip()]

    def is_model_allowed(self, model: str) -> bool:
        """Check if a LiteLLM model string is in the allowed list."""
        return model in self.get_allowed_models_list()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
