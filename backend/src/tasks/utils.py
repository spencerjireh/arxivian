"""Utilities for running async code in Celery tasks."""

import asyncio
from typing import TypeVar, Coroutine, Any

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run async coroutine in sync Celery task.

    Uses the persistent worker event loop if available (set up by signals.py),
    otherwise falls back to creating a temporary loop (useful for tests).

    Args:
        coro: The coroutine to execute

    Returns:
        The result of the coroutine
    """
    from src.tasks.signals import get_worker_loop

    loop = get_worker_loop()
    if loop is not None:
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        from src.config import get_settings

        return future.result(timeout=get_settings().celery_task_timeout)

    # Fallback: create a temporary loop (tests, non-worker contexts)
    tmp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(tmp_loop)
    try:
        return tmp_loop.run_until_complete(coro)
    finally:
        tmp_loop.close()
