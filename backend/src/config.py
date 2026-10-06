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

    # Semantic Scholar (demand signal -- citation velocity)
    # Key is optional: the keyless public pool works, just with tighter rate limits
    # (the client's backoff path handles 429s either way).
    semantic_scholar_api_key: str = ""
    semantic_scholar_cache_ttl_seconds: int = 604800  # 7 days
    # Keyless Semantic Scholar shares a ~1 req/s pool; this gate spaces our calls across
    # every worker (Redis slot) so concurrent scoring tasks cannot burst into 429s (ARX-17).
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

    # On-demand scoring (paper detail, ARX-12): Redis lock TTL that dedupes repeated
    # GET /papers/{id}/score polls into one score_paper_task per paper.
    ondemand_score_lock_seconds: int = 1800
    # Daily budget for on-demand scoring (ARX-35). Scoring is a shared cost, so the caps
    # are a global count across all users plus a flat per-user count, both per UTC day.
    ondemand_score_daily_budget: int = 30
    ondemand_score_daily_per_user: int = 10

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
    # Raised from 100 after ARX-70's coverage line showed every category stopping at
    # `max_results` with the window unexhausted: the crawl was seeing roughly the newest
    # quarter of the week, so the survivor cap was picking the best 150 of the newest 366
    # rather than of the week. Looking wider is nearly free -- Stage 1 is gpt-5-nano at
    # $0.05/M in, and `triage_max_survivors` still holds Stage 2 (and Semantic Scholar)
    # volume flat. Watch `stop_reason` in the `arxiv date scan` line: anything other than
    # `window_start` means this is still too low.
    triage_max_per_category: int = 500
    # Pause between per-category arXiv crawls so the weekly triage does not trip arXiv's
    # rate limit (ARX-16). The arxiv.Client keeps its own per-page delay on top.
    arxiv_crawl_pause_seconds: int = 3
    # Stage 1 classification calls run concurrently, not one after another. Sequential
    # batches put 4x100 candidates at ~33s per batch past celery_task_timeout, and the
    # SIGKILL discarded the whole run (ARX-67). Keep this modest: the cap exists to stay
    # inside the default model's rate limit, not to go as wide as possible.
    triage_batch_concurrency: int = 4
    # Ceiling on Stage 2 enqueues per run, highest rough_implementability first. Bounds
    # queue depth at --concurrency=2 so a keep-everything prompt regression cannot flood
    # the worker for hours; it is not a spend control (a full run is cents).
    triage_max_survivors: int = 150
    # Triage's own limit, overriding celery_task_timeout for this one task. The soft limit
    # fires first and is caught, so a slow run still enqueues the verdicts it already has
    # instead of losing all of them to the hard kill.
    triage_task_timeout: int = 3000

    # Stage 3 digest -- cached ranking snapshot for the current ISO week, rebuilt nightly.
    # Weekly was wrong: build_digest_task only ranks scores created inside the week, the feed
    # reads nothing but digest.ranking, and Stage 2 takes far longer than the 2h that used to
    # separate it from triage -- so anything scored later stayed invisible until the next
    # Monday (ARX-67). The build is an idempotent upsert, so re-running it nightly is safe.
    digest_schedule_cron: str = "0 8 * * *"  # Daily at 8am UTC


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # pydantic_settings reads from env
