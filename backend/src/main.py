"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings
from src.database import engine, init_db

# Import routers
from src.routers import health, ingest, search, stream, papers, conversations

# Import middleware
from src.middleware import logging_middleware, transaction_middleware, register_exception_handlers
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
    yield
    log.info("shutting down application")
    await engine.dispose()
    log.info("database connections closed")


app = FastAPI(
    title="Jireh's Agent System API",
    description="Jireh's Agent system for AI/ML research papers from arXiv",
    version="0.3.0",
    lifespan=lifespan,
)

# Register exception handlers first
register_exception_handlers(app)

# CORS middleware (must be first in middleware stack)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware (function-based, works with streaming)
app.middleware("http")(logging_middleware)

# Database transaction middleware (function-based, works with streaming)
app.middleware("http")(transaction_middleware)

# Register routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingest"])
app.include_router(stream.router, prefix="/api/v1", tags=["Stream"])
app.include_router(conversations.router, prefix="/api/v1", tags=["Conversations"])
app.include_router(papers.router, prefix="/api/v1", tags=["Papers"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Jireh's Agent System API",
        "version": "0.3.0",
        "features": [
            "Jireh's Agent with LangGraph",
            "Multi-provider LLM support (OpenAI, Z.AI)",
            "Hybrid search (vector + full-text)",
            "arXiv paper ingestion",
            "SSE streaming responses",
            "Conversation history management",
        ],
        "endpoints": {
            "health": "/api/v1/health",
            "search": "/api/v1/search",
            "ingest": "/api/v1/ingest",
            "stream": "/api/v1/stream",
            "papers": "/api/v1/papers",
            "conversations": "/api/v1/conversations",
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
