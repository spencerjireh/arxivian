"""Celery signal handlers: worker loop lifecycle and tracing.

Task status tracking lived here until ARX-74. It only ever issued UPDATEs and
no-op'd silently when no row existed, and nothing inserted rows for scheduled
tasks, so `task_executions` was permanently empty. Task outcomes live in Loki.
"""

import logfire
from celery.signals import (
    worker_process_init,
    worker_process_shutdown,
    worker_shutdown,
)

from src.database import engine
from src.observability import configure_tracing, flush
from src.tasks.runtime import start_worker_loop, stop_worker_loop
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
