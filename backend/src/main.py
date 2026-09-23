"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.database import AsyncSessionLocal, engine, init_db

# Import middleware
from src.middleware import logging_middleware, maintenance_middleware, register_exception_handlers
from src.observability import configure_tracing, flush
from src.routers import (
    conversations,
    feed,
    health,
    ops,
    paper_states,
    papers,
    stream,
    users,
    webhooks,
)

# Import routers
from src.schemas.errors import ErrorResponse
from src.services.agent_service.graph_builder import build_graph
from src.utils.logger import configure_logging, get_logger

settings = get_settings()

# Tracing before logging so the structlog processor finds a configured provider
configure_tracing("arxivian-api")
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

    litellm.suppress_debug_info = True  # type: ignore[invalid-assignment]
    litellm.set_verbose = False

    # Redis for rate limiting and caching
    import redis.asyncio as aioredis

    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    # Compile the agent graph once (singleton for app lifetime; no checkpointer -- every
    # turn is a single uninterrupted graph run since HITL was removed in Phase 3)
    app.state.agent_graph = build_graph()
    log.info("agent graph compiled")

    # Load system user ID (seeded by migration)
    from src.tiers import init_system_user

    async with AsyncSessionLocal() as db:
        await init_system_user(db)
    log.info("system user loaded")

    yield

    # Shutdown Redis (rate-limit client)
    await app.state.redis.aclose()

    log.info("shutting down application")
    await engine.dispose()
    log.info("database connections closed")
    flush()


app = FastAPI(
    title="Arxivian API",
    description="Arxivian - academic research assistant powered by arXiv",
    version="0.4.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    # Every route can answer with the error envelope from middleware/error_handler.py.
    responses={"default": {"model": ErrorResponse, "description": "Error envelope"}},
)

# Tracing: one span per request (health excluded) and per SQL statement
logfire.instrument_fastapi(app, excluded_urls="/api/v1/health")
logfire.instrument_sqlalchemy(engine=engine)

# Register exception handlers first
register_exception_handlers(app)

# CORS middleware (must be first in middleware stack)
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if not _cors_origins:
    log.warning("CORS_ORIGINS is empty; no cross-origin requests will be allowed")
app.add_middleware(
    CORSMiddleware,  # type: ignore[invalid-argument-type]
    allow_origins=_cors_origins,
    allow_credentials=bool(_cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Maintenance curtain (503 for all but health when MAINTENANCE_MODE is on).
# Registered before logging so logging stays outermost and still records the 503.
app.middleware("http")(maintenance_middleware)

# Request logging middleware (function-based, works with streaming)
app.middleware("http")(logging_middleware)

# Register routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(stream.router, prefix="/api/v1", tags=["Stream"])
app.include_router(conversations.router, prefix="/api/v1", tags=["Conversations"])
app.include_router(papers.router, prefix="/api/v1", tags=["Papers"])
app.include_router(ops.router, prefix="/api/v1", tags=["Ops"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])
app.include_router(feed.router, prefix="/api/v1", tags=["Feed"])
app.include_router(paper_states.router, prefix="/api/v1", tags=["Paper States"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"name": "Arxivian API", "status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
