"""Celery signals for worker lifecycle, Langfuse shutdown, and task status tracking."""

import asyncio
import threading

from celery.signals import (
    worker_process_init,
    worker_process_shutdown,
    worker_shutdown,
    task_prerun,
    task_success,
    task_failure,
)

from src.utils.logger import get_logger

log = get_logger(__name__)

# Module-level persistent event loop for the worker process
_worker_loop: asyncio.AbstractEventLoop | None = None
_worker_loop_thread: threading.Thread | None = None


def get_worker_loop() -> asyncio.AbstractEventLoop | None:
    """Get the persistent worker event loop, if available and not closed."""
    if _worker_loop is not None and not _worker_loop.is_closed():
        return _worker_loop
    return None


# ---------------------------------------------------------------------------
# 1. Worker event loop lifecycle (#7)
# ---------------------------------------------------------------------------


@worker_process_init.connect
def _on_worker_process_init(**kwargs) -> None:
    """Create a persistent event loop for the worker process."""
    global _worker_loop, _worker_loop_thread

    _worker_loop = asyncio.new_event_loop()

    def _run_loop():
        asyncio.set_event_loop(_worker_loop)
        _worker_loop.run_forever()

    _worker_loop_thread = threading.Thread(target=_run_loop, daemon=True)
    _worker_loop_thread.start()

    log.info("worker_event_loop_created")


@worker_process_shutdown.connect
def _on_worker_process_shutdown(**kwargs) -> None:
    """Close the persistent event loop on worker shutdown."""
    global _worker_loop, _worker_loop_thread

    if _worker_loop is not None and not _worker_loop.is_closed():
        _worker_loop.call_soon_threadsafe(_worker_loop.stop)
        if _worker_loop_thread is not None:
            _worker_loop_thread.join(timeout=5)
        _worker_loop.close()
        log.info("worker_event_loop_closed")

    _worker_loop = None
    _worker_loop_thread = None


# ---------------------------------------------------------------------------
# 2. Langfuse shutdown (#3)
# ---------------------------------------------------------------------------


@worker_shutdown.connect
def _on_worker_shutdown(**kwargs) -> None:
    """Flush and shutdown Langfuse client on worker shutdown."""
    from src.tasks.tracing import shutdown_task_langfuse

    shutdown_task_langfuse()
    log.info("langfuse_shutdown_on_worker_exit")


# ---------------------------------------------------------------------------
# 3. Task status tracking (#5)
# ---------------------------------------------------------------------------


def _update_task_execution_status(
    celery_task_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Update TaskExecution status in the database.

    Uses a sync DB update via run_async. No-op for tasks without
    a TaskExecution row (scheduled tasks). Catches and logs DB errors
    to avoid disrupting task execution.
    """
    try:
        from src.tasks.utils import run_async
        from src.database import AsyncSessionLocal
        from src.repositories.task_execution_repository import TaskExecutionRepository

        async def _do_update():
            async with AsyncSessionLocal() as session:
                repo = TaskExecutionRepository(session)
                await repo.update_status(celery_task_id, status, error_message)
                await session.commit()

        run_async(_do_update())
    except Exception:
        log.warning(
            "task_execution_status_update_failed",
            celery_task_id=celery_task_id,
            target_status=status,
            exc_info=True,
        )


@task_prerun.connect
def _on_task_prerun(task_id, **kwargs) -> None:
    """Mark task as started in the database."""
    _update_task_execution_status(task_id, "started")


@task_success.connect
def _on_task_success(sender, **kwargs) -> None:
    """Mark task as success in the database."""
    _update_task_execution_status(sender.request.id, "success")


@task_failure.connect
def _on_task_failure(task_id, exception, **kwargs) -> None:
    """Mark task as failure in the database with error message."""
    _update_task_execution_status(task_id, "failure", error_message=str(exception))
