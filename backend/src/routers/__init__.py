"""API routers."""

from src.routers import (
    health,
    ingest,
    search,
    stream,
    conversations,
    admin,
    papers,
    feedback,
    tasks,
    preferences,
)

__all__ = [
    "health",
    "ingest",
    "search",
    "stream",
    "conversations",
    "admin",
    "papers",
    "feedback",
    "tasks",
    "preferences",
]
