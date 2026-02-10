"""Registry for tracking active streaming tasks."""

import asyncio
from typing import Optional

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
        self._tasks: dict[str, tuple["asyncio.Task[None]", Optional[str]]] = {}

    def register(
        self, task_id: str, task: "asyncio.Task[None]", user_id: Optional[str] = None
    ) -> None:
        """
        Register a task with the given ID.

        Args:
            task_id: Unique identifier for the task (typically session_id)
            task: The asyncio task to register
            user_id: Optional owner user ID for ownership verification on cancel
        """
        self._tasks[task_id] = (task, user_id)
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

    def cancel(self, task_id: str, user_id: Optional[str] = None) -> bool:
        """
        Cancel a task by ID.

        Args:
            task_id: The task ID to cancel
            user_id: If provided, only cancel if this matches the registered owner

        Returns:
            True if a task was found and cancelled, False otherwise
        """
        entry = self._tasks.get(task_id)
        if entry is None:
            log.debug("task not found for cancellation", task_id=task_id)
            return False

        task, owner_id = entry
        if user_id is not None and owner_id is not None and user_id != owner_id:
            log.warning("cancel rejected: user_id mismatch", task_id=task_id)
            return False

        task.cancel()
        log.info("task cancelled", task_id=task_id)
        return True

    def is_active(self, task_id: str) -> bool:
        """
        Check if a task is currently active.

        Args:
            task_id: The task ID to check

        Returns:
            True if the task is registered and not done
        """
        entry = self._tasks.get(task_id)
        if entry is None:
            return False
        task, _ = entry
        return not task.done()

    def get(self, task_id: str) -> Optional["asyncio.Task[None]"]:
        """
        Get a task by ID.

        Args:
            task_id: The task ID to get

        Returns:
            The task if found, None otherwise
        """
        entry = self._tasks.get(task_id)
        if entry is None:
            return None
        task, _ = entry
        return task

    @property
    def active_count(self) -> int:
        """Return the number of active tasks."""
        return len(self._tasks)


# Global singleton instance
task_registry = TaskRegistry()
