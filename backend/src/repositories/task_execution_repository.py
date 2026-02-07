"""Repository for TaskExecution model operations."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.task_execution import TaskExecution
from src.utils.logger import get_logger

log = get_logger(__name__)

_TERMINAL_STATUSES = {"success", "failure"}


class TaskExecutionRepository:
    """Repository for TaskExecution CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        celery_task_id: str,
        user_id: UUID,
        task_type: str,
        parameters: Optional[dict] = None,
    ) -> TaskExecution:
        """Create a new task execution record."""
        task_exec = TaskExecution(
            celery_task_id=celery_task_id,
            user_id=user_id,
            task_type=task_type,
            parameters=parameters,
        )
        self.session.add(task_exec)
        await self.session.flush()
        await self.session.refresh(task_exec)
        log.debug("task_execution_created", celery_task_id=celery_task_id, task_type=task_type)
        return task_exec

    async def get_by_celery_task_id(self, celery_task_id: str) -> Optional[TaskExecution]:
        """Get task execution by Celery task ID."""
        result = await self.session.execute(
            select(TaskExecution).where(TaskExecution.celery_task_id == celery_task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_celery_task_id(
        self, user_id: UUID, celery_task_id: str
    ) -> Optional[TaskExecution]:
        """Get task execution by user ID and Celery task ID (ownership check)."""
        result = await self.session.execute(
            select(TaskExecution).where(
                TaskExecution.user_id == user_id,
                TaskExecution.celery_task_id == celery_task_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        celery_task_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Update task execution status. Sets completed_at on terminal states."""
        values: dict = {"status": status, "updated_at": func.now()}
        if error_message is not None:
            values["error_message"] = error_message
        if status in _TERMINAL_STATUSES:
            values["completed_at"] = func.now()

        await self.session.execute(
            update(TaskExecution)
            .where(TaskExecution.celery_task_id == celery_task_id)
            .values(**values)
        )

    async def list_by_user(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[TaskExecution], int]:
        """List task executions for a user with pagination."""
        count_result = await self.session.execute(
            select(func.count()).select_from(TaskExecution).where(TaskExecution.user_id == user_id)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(TaskExecution)
            .where(TaskExecution.user_id == user_id)
            .order_by(TaskExecution.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        tasks = list(result.scalars().all())
        return tasks, total
