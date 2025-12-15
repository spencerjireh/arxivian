"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings
from src.database import engine, init_db

# Import routers
from src.routers import health, ingest, search, ask_agent

# Import middleware
from src.middleware import LoggingMiddleware, TransactionMiddleware, register_exception_handlers
from src.utils.logger import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting application...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down application...")
    await engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title="Jireh's Agent System API",
    description="Jireh's Agent system for AI/ML research papers from arXiv",
    version="0.2.0",
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

# Request logging middleware
app.add_middleware(LoggingMiddleware)

# Database transaction middleware
app.add_middleware(TransactionMiddleware)

# Register routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingest"])
app.include_router(ask_agent.router, prefix="/api/v1", tags=["Ask"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Jireh's Agent System API",
        "version": "0.2.0",
        "features": [
            "Jireh's Agent with LangGraph",
            "Multi-provider LLM support (OpenAI, Z.AI)",
            "Hybrid search (vector + full-text)",
            "arXiv paper ingestion",
        ],
        "endpoints": {
            "health": "/api/v1/health",
            "search": "/api/v1/search",
            "ingest": "/api/v1/ingest",
            "ask_agent": "/api/v1/ask-agent",
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
