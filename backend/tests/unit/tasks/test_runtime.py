"""Unit tests for the worker event-loop runtime."""

import asyncio

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
