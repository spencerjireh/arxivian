"""Structlog-based logging with request context."""

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import Processor

# Context variable for request-scoped data
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

_configured = False


def add_request_id(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inject request_id from context into log event."""
    if req_id := request_id_ctx.get():
        event_dict["request_id"] = req_id
    return event_dict


def configure_logging(log_level: str = "INFO", debug: bool = False) -> None:
    """
    Configure structlog. Call once at startup.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        debug: Enable colored output for development
    """
    global _configured
    if _configured:
        return

    # Shared processors for all log entries
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        add_request_id,
    ]

    # Dev: colored key-value output
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=debug),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Suppress noisy third-party libraries (keep at WARNING+)
    for lib in ("httpx", "httpcore", "openai", "arxiv", "urllib3"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance.

    Args:
        name: Logger name, typically __name__ for module-scoped loggers

    Returns:
        Bound structlog logger

    Usage:
        from src.utils.logger import get_logger
        log = get_logger(__name__)
        log.info("processing", item_id=123, count=5)
    """
    return structlog.get_logger(name)


# Context helpers for request tracking
def set_request_id(request_id: str) -> None:
    """Set request ID in context for current async task."""
    request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    """Get request ID from context."""
    return request_id_ctx.get()


def clear_request_id() -> None:
    """Clear request ID from context."""
    request_id_ctx.set(None)


def truncate(text: str, max_len: int = 1000) -> str:
    """Truncate text for logging, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
