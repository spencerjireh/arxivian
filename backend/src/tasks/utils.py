"""Utilities for running async code in Celery tasks."""

import asyncio
from typing import TypeVar, Coroutine, Any

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run async coroutine in sync Celery task.

    Creates a new event loop for each task execution to avoid
    issues with shared loops across worker processes.

    Args:
        coro: The coroutine to execute

    Returns:
        The result of the coroutine
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
