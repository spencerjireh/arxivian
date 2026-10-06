"""Worker event-loop runtime: one persistent asyncio loop per Celery worker process.

`signals.py` starts and stops the loop on worker process init/shutdown; tasks call
`run_async` to execute a coroutine on it. Outside a worker (tests, one-off scripts) there
is no loop and `run_async` falls back to a temporary one.
"""

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

from src.config import get_settings
from src.utils.logger import get_logger

log = get_logger(__name__)

T = TypeVar("T")

_worker_loop: asyncio.AbstractEventLoop | None = None
_worker_loop_thread: threading.Thread | None = None


def get_worker_loop() -> asyncio.AbstractEventLoop | None:
    """Return the persistent worker loop, or None when absent or closed."""
    if _worker_loop is not None and not _worker_loop.is_closed():
        return _worker_loop
    return None


def start_worker_loop() -> None:
    """Create the persistent loop and run it forever on a daemon thread."""
    global _worker_loop, _worker_loop_thread

    _worker_loop = asyncio.new_event_loop()

    def _run_loop():
        asyncio.set_event_loop(_worker_loop)
        _worker_loop.run_forever()

    _worker_loop_thread = threading.Thread(target=_run_loop, daemon=True)
    _worker_loop_thread.start()
    log.info("worker_event_loop_created")


def stop_worker_loop() -> None:
    """Stop and close the persistent loop; no-op when it was never started."""
    global _worker_loop, _worker_loop_thread

    if _worker_loop is not None and not _worker_loop.is_closed():
        _worker_loop.call_soon_threadsafe(_worker_loop.stop)
        if _worker_loop_thread is not None:
            _worker_loop_thread.join(timeout=5)
        _worker_loop.close()
        log.info("worker_event_loop_closed")

    _worker_loop = None
    _worker_loop_thread = None


def run_async(coro: Coroutine[Any, Any, T], timeout: float | None = None) -> T:
    """Run a coroutine from a sync Celery task and return its result.

    Uses the persistent worker loop when one exists; otherwise runs it on a temporary loop.

    `timeout` defaults to `Settings.celery_task_timeout`. A task that raises its own Celery
    `soft_time_limit` above that default MUST pass a matching value here, or this bound
    fires first and the task's own limit never applies -- which is what killed the weekly
    triage at 600s despite a 3000s soft limit (ARX-72).
    """
    loop = get_worker_loop()
    if loop is not None:
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=timeout or get_settings().celery_task_timeout)
        except TimeoutError:
            # future.result() timing out does NOT stop the coroutine -- it keeps running on
            # the shared worker loop, burning API calls and still writing, long after the
            # task is marked failed. Cancel it so a failed task means stopped work.
            future.cancel()
            raise

    tmp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(tmp_loop)
    try:
        return tmp_loop.run_until_complete(coro)
    finally:
        tmp_loop.close()
