"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    postgres_url: str = "postgresql+asyncpg://user:password@localhost:5432/arxiv_rag"

    # LLM Configuration (LiteLLM-format model strings: "provider/model"). One model for
    # every chat/triage call; there is no per-request model selection (Phase 3).
    default_llm_model: str = "openai/gpt-5-nano"
    # Model override for structured-output calls (classify_and_route, evaluate_batch, triage).
    # None means use default_llm_model.
    structured_output_model: str | None = "openai/gpt-5-nano"
    default_temperature: float = 0.3

    # Provider API Keys
    openai_api_key: str = ""

    # Embeddings
    jina_api_key: str = ""

    # Semantic Scholar (demand signal -- citation velocity)
    # Key is optional: the keyless public pool works, just with tighter rate limits
    # (the client's backoff path handles 429s either way).
    semantic_scholar_api_key: str = ""
    semantic_scholar_cache_ttl_seconds: int = 604800  # 7 days
    # Keyless Semantic Scholar shares a ~1 req/s pool; this gate spaces our calls across
    # every worker (Redis slot) so concurrent scoring tasks cannot burst into 429s (SPE-284).
    semantic_scholar_min_interval_ms: int = 1500
    # Nightly backfill of demand for scores whose S2 lookup soft-failed to NULL.
    demand_backfill_schedule_cron: str = "0 4 * * *"  # Daily at 4am UTC
    demand_backfill_batch_size: int = 200

    # TypeSafe Jev -- the Stage 2 scoring judgment engine (method clarity, resource
    # feasibility, data availability, product attributes). Key is required for scoring;
    # the client is only constructed inside the scoring task, never at import.
    typesafe_api_key: str = ""
    typesafe_model: str = "jev-1.13.0"
    typesafe_timeout_seconds: int = 60

    # On-demand scoring (paper detail, SPE-276): Redis lock TTL that dedupes repeated
    # GET /papers/{id}/score polls into one score_paper_task per paper.
    ondemand_score_lock_seconds: int = 1800

    # Search configuration
    default_top_k: int = 3
    rrf_k: int = 60

    # Chunking configuration
    chunk_size_words: int = 600
    chunk_overlap_words: int = 100
    min_chunk_words: int = 100

    # Agent Configuration (paper-scoped chat)
    guardrail_threshold: int = 75  # scope score below this is answered as out of scope
    max_iterations: int = 5  # classify -> execute -> evaluate loops per turn
    conversation_window: int = 5  # previous turns included in the prompt

    # Request Lifecycle Configuration
    agent_timeout_seconds: int = 180  # 3 minutes max per request
    llm_call_timeout_seconds: int = 60  # 1 minute per LLM call

    # Redis
    redis_url: str = "redis://redis:6379/2"

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

    # Tracing: Logfire reads LOGFIRE_TOKEN / LOGFIRE_ENVIRONMENT itself (src/observability.py).

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
    # Pause between per-category arXiv crawls so the weekly triage does not trip arXiv's
    # rate limit (SPE-283). The arxiv.Client keeps its own per-page delay on top.
    arxiv_crawl_pause_seconds: int = 3

    # Stage 3 digest -- weekly cached ranking snapshot. Runs after triage+scoring settle.
    digest_schedule_cron: str = "0 8 * * 1"  # Weekly Monday 8am UTC (2h after triage)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # pydantic_settings reads from env
