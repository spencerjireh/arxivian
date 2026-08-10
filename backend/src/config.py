"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    postgres_url: str = "postgresql+asyncpg://user:password@localhost:5432/arxiv_rag"

    # LLM Configuration (LiteLLM-format model strings: "provider/model")
    default_llm_model: str = "openai/gpt-5-nano"
    allowed_llm_models: str = "openai/gpt-5-nano,nvidia_nim/openai/gpt-oss-120b,openai/gpt-4o-mini"
    # Model override for structured output calls (router, guardrail, grading).
    # None means use default_llm_model.
    structured_output_model: str | None = "openai/gpt-5-nano"

    # Provider API Keys
    openai_api_key: str = ""
    nvidia_nim_api_key: str | None = None
    nvidia_nim_api_base: str | None = None

    # Embeddings
    jina_api_key: str = ""

    # Semantic Scholar (demand signal -- citation velocity)
    # Key is optional: the keyless public pool works, just with tighter rate limits
    # (the client's backoff path handles 429s either way).
    semantic_scholar_api_key: str = ""
    semantic_scholar_cache_ttl_seconds: int = 604800  # 7 days

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

    # Redis
    redis_url: str = "redis://redis:6379/2"
    # RediSearch (used by langgraph-checkpoint-redis) only works on DB 0
    redis_checkpoint_url: str = "redis://redis:6379/0"

    # CORS
    cors_origins: str = (
        ""  # comma-separated allowed origins; empty = block all cross-origin requests
    )

    # App
    debug: bool = False
    sql_echo: bool = False
    log_level: str = "INFO"
    log_request_body: bool = True
    log_response_body: bool = True
    # When true, all API routes except health return 503 (pivot maintenance curtain).
    maintenance_mode: bool = False

    # Langfuse Observability
    langfuse_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "http://langfuse:3000"  # Self-hosted default

    # Clerk Authentication
    clerk_domain: str  # e.g. "your-app.clerk.accounts.dev"
    clerk_jwt_audience: str = ""
    clerk_webhook_secret: str = ""

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

    # Stage 1 triage (scoring pipeline entry point)
    triage_schedule_cron: str = "0 6 * * 1"  # Weekly Monday 6am UTC
    triage_categories: list[str] = ["cs.LG", "cs.CL", "cs.CV", "cs.AI"]
    triage_lookback_days: int = 7
    triage_max_per_category: int = 100

    # Stage 3 digest -- weekly cached ranking snapshot. Runs after triage+scoring settle.
    digest_schedule_cron: str = "0 8 * * 1"  # Weekly Monday 8am UTC (2h after triage)

    # Stage 2 scoring -- model for the two LLM-judged dimensions (method clarity,
    # resource feasibility). Must be in allowed_llm_models.
    scoring_strong_model: str = "openai/gpt-5-nano"

    # Helper methods
    def get_allowed_models_list(self) -> list[str]:
        """Get list of all allowed LiteLLM model strings."""
        return [m.strip() for m in self.allowed_llm_models.split(",") if m.strip()]

    def is_model_allowed(self, model: str) -> bool:
        """Check if a LiteLLM model string is in the allowed list."""
        return model in self.get_allowed_models_list()

    @model_validator(mode="after")
    def _check_referenced_models_allowed(self) -> "Settings":
        """Fail fast at startup if a referenced LLM model is not in ALLOWED_LLM_MODELS.

        The default/structured/scoring models must all be in the allowlist, or
        `get_llm_client()` raises `InvalidModelError` deep inside a Celery task at runtime
        (the SPE-282 env-drift bug). This turns that into a clear boot-time error in every
        entrypoint (web, worker, beat, shell), since each builds `Settings` at import.

        `structured_output_model` is optional -- empty/None means "use the default" -- so it
        is only checked when set, mirroring `get_llm_client`'s `structured_output_model or None`.
        """
        allowed = self.get_allowed_models_list()
        referenced = {
            "default_llm_model": self.default_llm_model,
            "scoring_strong_model": self.scoring_strong_model,
        }
        if self.structured_output_model:
            referenced["structured_output_model"] = self.structured_output_model

        missing = {name: model for name, model in referenced.items() if model not in allowed}
        if missing:
            offending = ", ".join(f"{name}={model!r}" for name, model in missing.items())
            # Raise a plain RuntimeError, not ValueError: pydantic wraps ValueError into a
            # ValidationError whose repr dumps the whole settings dict (leaking secrets like
            # postgres_url / API keys into crash logs). RuntimeError propagates cleanly with
            # only this message.
            raise RuntimeError(
                f"LLM model(s) not in ALLOWED_LLM_MODELS {allowed}: {offending}. "
                "Add them to ALLOWED_LLM_MODELS (see backend/.env.example) or change the "
                "model setting -- otherwise get_llm_client() crashes at runtime."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # ty: ignore[missing-argument]  # pydantic_settings reads from env
