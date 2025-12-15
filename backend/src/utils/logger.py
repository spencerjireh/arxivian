"""Structured logging utility with context support."""

import logging
import sys
from contextvars import ContextVar
from typing import Any, Optional

from src.config import get_settings

# Context variables for request-scoped data
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

settings = get_settings()


class ContextFilter(logging.Filter):
    """Add context variables to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id to log record if available."""
        record.request_id = request_id_var.get()
        return True


class ColoredFormatter(logging.Formatter):
    """Colored formatter for human-readable logs in development."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{self.BOLD}{levelname}{self.RESET}"

        # Format the message
        formatted = super().format(record)

        return formatted


def setup_logger(name: str = "jirehs_agent") -> logging.Logger:
    """
    Configure and return application logger.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Console handler with colored output for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Human-readable format for development
    if settings.debug:
        formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(request_id)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # Simpler format for production
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Add context filter
    context_filter = ContextFilter()
    console_handler.addFilter(context_filter)

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get request ID from context."""
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear request ID from context."""
    request_id_var.set(None)


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs: Any) -> None:
    """
    Log message with additional context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **kwargs: Additional context to include
    """
    extra = {"extra_context": kwargs} if kwargs else {}
    log_func = getattr(logger, level.lower())
    log_func(message, extra=extra)


# Default logger instance
logger = setup_logger()
