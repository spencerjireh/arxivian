"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings
from src.database import engine, init_db, AsyncSessionLocal

from src.services.agent_service.graph_builder import build_graph

# Import routers
from src.routers import (
    health,
    search,
    stream,
    papers,
    conversations,
    ops,
    feedback,
    users,
)

# Import middleware
from src.middleware import logging_middleware, register_exception_handlers
from src.utils.logger import configure_logging, get_logger

settings = get_settings()

# Configure logging early
configure_logging(log_level=settings.log_level, debug=settings.debug)
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    log.info("starting application", debug=settings.debug, log_level=settings.log_level)
    await init_db()
    log.info("database initialized")

    # Configure LiteLLM
    import litellm

    litellm.suppress_debug_info = True
    litellm.set_verbose = False

    if settings.langfuse_enabled:
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]
        log.info("langfuse_enabled", host=settings.langfuse_host)

    # Redis for rate limiting and caching
    import redis.asyncio as aioredis

    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    # Initialize LangGraph checkpointer (must use Redis DB 0 for RediSearch)
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver

    async with AsyncRedisSaver.from_conn_string(
        settings.redis_checkpoint_url,
        ttl={"default_ttl": 60 * 24, "refresh_on_read": False},  # 24h in minutes
    ) as checkpointer:
        await checkpointer.asetup()
        log.info("redis checkpointer initialized", url=settings.redis_checkpoint_url)

        # Compile agent graph once with checkpointer (singleton for app lifetime)
        app.state.agent_graph = build_graph(checkpointer)
        log.info("agent graph compiled with checkpointer")

        # Load system user ID (seeded by migration)
        from src.tiers import init_system_user

        async with AsyncSessionLocal() as db:
            await init_system_user(db)
        log.info("system user loaded")

        yield

    # Shutdown Redis (rate-limit client)
    await app.state.redis.aclose()

    # Flush any pending Langfuse events on shutdown
    try:
        from src.clients.langfuse_utils import shutdown_langfuse

        shutdown_langfuse()
    except Exception as e:
        log.warning("langfuse_shutdown_failed", error=str(e))

    log.info("shutting down application")
    await engine.dispose()
    log.info("database connections closed")


app = FastAPI(
    title="Arxivian API",
    description="Arxivian - academic research assistant powered by arXiv",
    version="0.4.0",
    lifespan=lifespan,
)

# Register exception handlers first
register_exception_handlers(app)

# CORS middleware (must be first in middleware stack)
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=bool(_cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware (function-based, works with streaming)
app.middleware("http")(logging_middleware)

# Register routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(stream.router, prefix="/api/v1", tags=["Stream"])
app.include_router(conversations.router, prefix="/api/v1", tags=["Conversations"])
app.include_router(papers.router, prefix="/api/v1", tags=["Papers"])
app.include_router(ops.router, prefix="/api/v1", tags=["Ops"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Arxivian API",
        "version": "0.4.0",
        "features": [
            "Agentic RAG with LangGraph",
            "Multi-provider LLM support (OpenAI, NVIDIA NIM) via LiteLLM",
            "Hybrid search (vector + full-text)",
            "arXiv paper ingestion",
            "SSE streaming responses",
            "Conversation history management",
            "User tiers (Free, Pro)",
        ],
        "endpoints": {
            "health": "/api/v1/health",
            "search": "/api/v1/search",
            "stream": "/api/v1/stream",
            "papers": "/api/v1/papers",
            "conversations": "/api/v1/conversations",
            "ops": "/api/v1/ops",
            "users": "/api/v1/users",
        },
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
