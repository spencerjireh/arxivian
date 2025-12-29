"""Registry for tracking active streaming tasks."""

import asyncio
from typing import Dict, Optional

from src.utils.logger import get_logger

log = get_logger(__name__)


class TaskRegistry:
    """
    Registry for tracking active streaming tasks.

    Safe for single-threaded async use within one event loop.
    Allows cancellation of running streams via their task IDs.
    """

    def __init__(self) -> None:
        """Initialize the task registry."""
        self._tasks: Dict[str, "asyncio.Task[None]"] = {}

    def register(self, task_id: str, task: "asyncio.Task[None]") -> None:
        """
        Register a task with the given ID.

        Args:
            task_id: Unique identifier for the task (typically session_id)
            task: The asyncio task to register
        """
        self._tasks[task_id] = task
        log.debug("task registered", task_id=task_id, active_tasks=len(self._tasks))

    def unregister(self, task_id: str) -> None:
        """
        Unregister a task by ID.

        Args:
            task_id: The task ID to unregister
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            log.debug("task unregistered", task_id=task_id, active_tasks=len(self._tasks))

    def cancel(self, task_id: str) -> bool:
        """
        Cancel a task by ID.

        Args:
            task_id: The task ID to cancel

        Returns:
            True if a task was found and cancelled, False otherwise
        """
        task = self._tasks.get(task_id)
        if task is not None:
            task.cancel()
            log.info("task cancelled", task_id=task_id)
            return True
        log.debug("task not found for cancellation", task_id=task_id)
        return False

    def is_active(self, task_id: str) -> bool:
        """
        Check if a task is currently active.

        Args:
            task_id: The task ID to check

        Returns:
            True if the task is registered and not done
        """
        task = self._tasks.get(task_id)
        return task is not None and not task.done()

    def get(self, task_id: str) -> Optional["asyncio.Task[None]"]:
        """
        Get a task by ID.

        Args:
            task_id: The task ID to get

        Returns:
            The task if found, None otherwise
        """
        return self._tasks.get(task_id)

    @property
    def active_count(self) -> int:
        """Return the number of active tasks."""
        return len(self._tasks)


# Global singleton instance
task_registry = TaskRegistry()
