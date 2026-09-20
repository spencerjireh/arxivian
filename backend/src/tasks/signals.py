"""Celery signal handlers: worker loop lifecycle, tracing, and task status tracking."""

import logfire
from celery.signals import (
    task_failure,
    task_prerun,
    task_success,
    worker_process_init,
    worker_process_shutdown,
    worker_shutdown,
)

from src.database import AsyncSessionLocal, engine
from src.observability import configure_tracing, flush
from src.repositories.task_execution_repository import TaskExecutionRepository
from src.tasks.runtime import run_async, start_worker_loop, stop_worker_loop
from src.utils.logger import get_logger

log = get_logger(__name__)


@worker_process_init.connect
def _on_worker_process_init(**_kwargs) -> None:
    """Start the worker event loop and per-process tracing."""
    start_worker_loop()
    # Tracing is per forked process: exporter, Celery task spans, SQL spans.
    configure_tracing("arxivian-worker")
    logfire.instrument_celery()
    logfire.instrument_sqlalchemy(engine=engine)


@worker_process_shutdown.connect
def _on_worker_process_shutdown(**_kwargs) -> None:
    """Close the worker event loop."""
    stop_worker_loop()


@worker_shutdown.connect
def _on_worker_shutdown(**_kwargs) -> None:
    """Flush pending spans on worker shutdown."""
    flush()
    log.info("tracing_flushed_on_worker_exit")


def _update_task_execution_status(
    celery_task_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Update the TaskExecution row for a task; no-op when there is none.

    DB errors are logged, never raised, so a status update cannot break a task.
    """
    try:

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
def _on_task_prerun(task_id, **_kwargs) -> None:
    _update_task_execution_status(task_id, "started")


@task_success.connect
def _on_task_success(sender, **_kwargs) -> None:
    _update_task_execution_status(sender.request.id, "success")


@task_failure.connect
def _on_task_failure(task_id, exception, **_kwargs) -> None:
    _update_task_execution_status(task_id, "failure", error_message=str(exception))
