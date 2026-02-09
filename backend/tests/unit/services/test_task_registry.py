"""Tests for TaskRegistry service."""

import asyncio
from unittest.mock import Mock

from src.services.task_registry import TaskRegistry


class TestTaskRegistryRegister:
    """Tests for TaskRegistry.register method."""

    def test_register_adds_task_to_registry(self):
        """Verify task is stored after registration."""
        registry = TaskRegistry()
        mock_task = Mock(spec=asyncio.Task)

        registry.register("task-1", mock_task)

        assert "task-1" in registry._tasks
        assert registry._tasks["task-1"] is mock_task

    def test_register_updates_active_count(self):
        """Verify active_count increments after registration."""
        registry = TaskRegistry()
        mock_task = Mock(spec=asyncio.Task)

        assert registry.active_count == 0
        registry.register("task-1", mock_task)
        assert registry.active_count == 1

    def test_register_multiple_tasks(self):
        """Verify multiple tasks can be registered."""
        registry = TaskRegistry()
        task1 = Mock(spec=asyncio.Task)
        task2 = Mock(spec=asyncio.Task)

        registry.register("task-1", task1)
        registry.register("task-2", task2)

        assert registry.active_count == 2
        assert registry._tasks["task-1"] is task1
        assert registry._tasks["task-2"] is task2

    def test_register_overwrites_existing_task(self):
        """Verify registering with same ID overwrites previous task."""
        registry = TaskRegistry()
        task1 = Mock(spec=asyncio.Task)
        task2 = Mock(spec=asyncio.Task)

        registry.register("task-1", task1)
        registry.register("task-1", task2)

        assert registry.active_count == 1
        assert registry._tasks["task-1"] is task2


class TestTaskRegistryUnregister:
    """Tests for TaskRegistry.unregister method."""

    def test_unregister_removes_task(self):
        """Verify task is removed from registry."""
        registry = TaskRegistry()
        mock_task = Mock(spec=asyncio.Task)
        registry.register("task-1", mock_task)

        registry.unregister("task-1")

        assert "task-1" not in registry._tasks
        assert registry.active_count == 0

    def test_unregister_nonexistent_task_is_noop(self):
        """Verify no error when unregistering unknown task."""
        registry = TaskRegistry()

        # Should not raise
        registry.unregister("nonexistent")

        assert registry.active_count == 0

    def test_unregister_only_removes_specified_task(self):
        """Verify only the specified task is removed."""
        registry = TaskRegistry()
        task1 = Mock(spec=asyncio.Task)
        task2 = Mock(spec=asyncio.Task)
        registry.register("task-1", task1)
        registry.register("task-2", task2)

        registry.unregister("task-1")

        assert "task-1" not in registry._tasks
        assert "task-2" in registry._tasks
        assert registry.active_count == 1


class TestTaskRegistryCancel:
    """Tests for TaskRegistry.cancel method."""

    def test_cancel_running_task_returns_true(self):
        """Verify cancellation of active task returns True."""
        registry = TaskRegistry()
        mock_task = Mock(spec=asyncio.Task)
        registry.register("task-1", mock_task)

        result = registry.cancel("task-1")

        assert result is True

    def test_cancel_calls_task_cancel(self):
        """Verify asyncio.Task.cancel() is called."""
        registry = TaskRegistry()
        mock_task = Mock(spec=asyncio.Task)
        registry.register("task-1", mock_task)

        registry.cancel("task-1")

        mock_task.cancel.assert_called_once()

    def test_cancel_nonexistent_task_returns_false(self):
        """Verify False when task not found."""
        registry = TaskRegistry()

        result = registry.cancel("nonexistent")

        assert result is False

    def test_cancel_does_not_remove_task_from_registry(self):
        """Verify cancel does not automatically unregister the task."""
        registry = TaskRegistry()
        mock_task = Mock(spec=asyncio.Task)
        registry.register("task-1", mock_task)

        registry.cancel("task-1")

        # Task should still be in registry (caller should unregister)
        assert "task-1" in registry._tasks


class TestTaskRegistryIsActive:
    """Tests for TaskRegistry.is_active method."""

    def test_is_active_returns_true_for_running_task(self):
        """Verify active status for running task."""
        registry = TaskRegistry()
        mock_task = Mock(spec=asyncio.Task)
        mock_task.done.return_value = False
        registry.register("task-1", mock_task)

        result = registry.is_active("task-1")

        assert result is True

    def test_is_active_returns_false_for_done_task(self):
        """Verify False when task.done() returns True."""
        registry = TaskRegistry()
        mock_task = Mock(spec=asyncio.Task)
        mock_task.done.return_value = True
        registry.register("task-1", mock_task)

        result = registry.is_active("task-1")

        assert result is False

    def test_is_active_returns_false_for_unknown_task(self):
        """Verify False for non-existent task."""
        registry = TaskRegistry()

        result = registry.is_active("nonexistent")

        assert result is False


class TestTaskRegistryGet:
    """Tests for TaskRegistry.get method."""

    def test_get_returns_task_for_known_id(self):
        """Verify correct task is returned."""
        registry = TaskRegistry()
        mock_task = Mock(spec=asyncio.Task)
        registry.register("task-1", mock_task)

        result = registry.get("task-1")

        assert result is mock_task

    def test_get_returns_none_for_unknown_id(self):
        """Verify None for non-existent task."""
        registry = TaskRegistry()

        result = registry.get("nonexistent")

        assert result is None


class TestTaskRegistryActiveCount:
    """Tests for TaskRegistry.active_count property."""

    def test_active_count_starts_at_zero(self):
        """Verify initial count is zero."""
        registry = TaskRegistry()

        assert registry.active_count == 0

    def test_active_count_reflects_registry_size(self):
        """Verify count matches registered tasks."""
        registry = TaskRegistry()
        for i in range(5):
            mock_task = Mock(spec=asyncio.Task)
            registry.register(f"task-{i}", mock_task)

        assert registry.active_count == 5

    def test_active_count_updates_on_unregister(self):
        """Verify count decreases on unregister."""
        registry = TaskRegistry()
        for i in range(3):
            mock_task = Mock(spec=asyncio.Task)
            registry.register(f"task-{i}", mock_task)

        registry.unregister("task-0")
        registry.unregister("task-1")

        assert registry.active_count == 1
