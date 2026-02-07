"""Langfuse tracing utilities shared across the application.

Provides trace context management and a singleton Langfuse client
for nesting LLM generations under LangGraph traces.
"""

from contextvars import ContextVar
from typing import Optional

from src.utils.logger import get_logger

log = get_logger(__name__)

# Context variable for trace hierarchy - allows LLM calls to nest under the graph trace
_current_trace_id: ContextVar[str | None] = ContextVar("langfuse_trace_id", default=None)


def set_trace_context(trace_id: str | None) -> None:
    """Set the current Langfuse trace ID for nested LLM call tracing.

    Call this before executing LLM operations to ensure generations
    are nested under the parent trace (e.g., from LangGraph CallbackHandler).

    Args:
        trace_id: The parent trace ID, or None to clear context.
    """
    _current_trace_id.set(trace_id)


def get_trace_context() -> str | None:
    """Get the current Langfuse trace ID.

    Returns:
        The current trace ID if set, None otherwise.
    """
    return _current_trace_id.get()


# Lazy Langfuse initialization
_langfuse_client = None
LANGFUSE_AVAILABLE = False

try:
    from langfuse import Langfuse

    LANGFUSE_AVAILABLE = True
except ImportError:
    Langfuse = None  # type: ignore[misc, assignment]


def get_langfuse() -> Optional["Langfuse"]:  # type: ignore[name-defined]
    """Get or create singleton Langfuse client."""
    global _langfuse_client
    if not LANGFUSE_AVAILABLE:
        return None
    if _langfuse_client is None:
        from src.config import get_settings

        settings = get_settings()
        if settings.langfuse_enabled:
            if not settings.langfuse_public_key or not settings.langfuse_secret_key:
                log.warning(
                    "langfuse_keys_missing",
                    message="Langfuse is enabled but API keys are not configured. Tracing disabled.",
                )
                return None
            _langfuse_client = Langfuse(  # type: ignore[misc]
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            log.info("langfuse_client_initialized")
    return _langfuse_client


def shutdown_langfuse() -> None:
    """Flush and shutdown singleton Langfuse client.

    Call this during application shutdown to ensure all pending
    events are sent before the process exits.
    """
    global _langfuse_client
    if _langfuse_client is not None:
        _langfuse_client.flush()
        _langfuse_client.shutdown()
        _langfuse_client = None
        log.info("langfuse_shutdown")
