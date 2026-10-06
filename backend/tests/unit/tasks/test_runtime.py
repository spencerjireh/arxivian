"""Unit tests for the worker event-loop runtime."""

import asyncio
import time

import pytest

import src.tasks.runtime as runtime


def _reset() -> None:
    runtime._worker_loop = None
    runtime._worker_loop_thread = None


class TestWorkerLoopLifecycle:
    def test_start_creates_running_loop(self):
        _reset()
        runtime.start_worker_loop()

        assert runtime._worker_loop is not None
        assert not runtime._worker_loop.is_closed()
        assert runtime._worker_loop_thread is not None
        assert runtime._worker_loop_thread.is_alive()

        runtime.stop_worker_loop()

    def test_stop_closes_loop_and_clears_state(self):
        _reset()
        runtime.start_worker_loop()
        loop = runtime._worker_loop
        assert loop is not None

        runtime.stop_worker_loop()

        assert runtime._worker_loop is None
        assert runtime._worker_loop_thread is None
        assert loop.is_closed()

    def test_stop_is_noop_when_never_started(self):
        _reset()
        runtime.stop_worker_loop()
        assert runtime._worker_loop is None


class TestGetWorkerLoop:
    def test_returns_loop_when_running(self):
        _reset()
        runtime.start_worker_loop()

        loop = runtime.get_worker_loop()
        assert loop is not None
        assert not loop.is_closed()

        runtime.stop_worker_loop()

    def test_returns_none_when_not_initialized(self):
        _reset()
        assert runtime.get_worker_loop() is None

    def test_returns_none_when_closed(self):
        loop = asyncio.new_event_loop()
        loop.close()
        runtime._worker_loop = loop

        assert runtime.get_worker_loop() is None
        _reset()


class TestRunAsync:
    def test_uses_temporary_loop_without_worker(self):
        _reset()

        async def add(a: int, b: int) -> int:
            return a + b

        assert runtime.run_async(add(2, 3)) == 5

    def test_uses_worker_loop_when_running(self):
        _reset()
        runtime.start_worker_loop()

        async def which_loop() -> asyncio.AbstractEventLoop:
            return asyncio.get_running_loop()

        try:
            assert runtime.run_async(which_loop()) is runtime._worker_loop
        finally:
            runtime.stop_worker_loop()

    def test_explicit_timeout_overrides_the_celery_default(self):
        """A task whose own limit exceeds celery_task_timeout must be able to say so.

        Without this, run_async bounded every task at celery_task_timeout no matter what
        soft_time_limit the task declared, which killed the weekly triage at 600s against
        its own 3000s limit (ARX-72).
        """
        _reset()
        runtime.start_worker_loop()

        async def slow() -> str:
            await asyncio.sleep(0.3)
            return "finished"

        try:
            # celery_task_timeout is 600 in tests, so the default would not catch this;
            # a short explicit timeout proves the argument is what bounds the call.
            with pytest.raises(TimeoutError):
                runtime.run_async(slow(), timeout=0.05)
            # And a generous one lets the same coroutine through.
            assert runtime.run_async(slow(), timeout=5) == "finished"
        finally:
            runtime.stop_worker_loop()

    def test_timeout_cancels_the_coroutine_instead_of_orphaning_it(self):
        """A failed task must mean stopped work, not work that keeps running unobserved."""
        _reset()
        runtime.start_worker_loop()
        ran_to_completion = False

        async def long() -> None:
            nonlocal ran_to_completion
            await asyncio.sleep(0.5)
            ran_to_completion = True

        try:
            with pytest.raises(TimeoutError):
                runtime.run_async(long(), timeout=0.05)
            # Give the loop more than the coroutine's own duration; it must stay cancelled.
            time.sleep(0.8)
            assert ran_to_completion is False
        finally:
            runtime.stop_worker_loop()
