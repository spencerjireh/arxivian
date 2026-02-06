"""Langfuse tracing utilities for Celery tasks."""

from contextlib import contextmanager
from typing import Any, Generator, Optional

from src.config import get_settings
from src.utils.logger import get_logger

log = get_logger(__name__)

# Lazy Langfuse initialization for workers
_langfuse_client = None


def _get_langfuse():
    """Get or create singleton Langfuse client for worker process."""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client

    settings = get_settings()
    if not settings.langfuse_enabled:
        return None

    try:
        from langfuse import Langfuse

        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            log.warning("langfuse_keys_missing_for_tasks")
            return None

        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        log.info("langfuse_initialized_for_tasks")
        return _langfuse_client

    except ImportError:
        log.debug("langfuse_not_installed")
        return None


@contextmanager
def trace_task(
    task_name: str,
    task_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> Generator[Optional[Any], None, None]:
    """Context manager for tracing Celery tasks with Langfuse.

    Creates a trace for the task execution, automatically handling
    success/failure status and flushing on completion.

    Args:
        task_name: Name of the Celery task
        task_id: Celery task ID
        metadata: Additional metadata to include in the trace

    Yields:
        The Langfuse trace object (or None if Langfuse is disabled)

    Example:
        @celery_app.task(bind=True)
        def my_task(self, arg1):
            with trace_task("my_task", self.request.id, {"arg1": arg1}) as trace:
                # Do work...
                if trace:
                    trace.span(name="step1", ...)
    """
    langfuse = _get_langfuse()
    if langfuse is None:
        yield None
        return

    trace = langfuse.trace(
        name=f"celery_{task_name}",
        metadata={
            "task_id": task_id,
            "task_name": task_name,
            **(metadata or {}),
        },
    )

    try:
        yield trace
        trace.update(metadata={"status": "success"})
    except Exception as e:
        trace.update(
            metadata={"status": "error", "error": str(e)},
        )
        raise
    finally:
        # Ensure trace is flushed before task completes
        try:
            langfuse.flush()
        except Exception:
            pass


def shutdown_task_langfuse() -> None:
    """Shutdown Langfuse client in worker process.

    Call this on worker shutdown to ensure all traces are flushed.
    """
    global _langfuse_client
    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
            _langfuse_client.shutdown()
        except Exception:
            pass
        _langfuse_client = None
        log.info("langfuse_shutdown_for_tasks")
