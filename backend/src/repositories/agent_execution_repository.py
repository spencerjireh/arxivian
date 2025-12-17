"""Repository for AgentExecution model operations."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.agent_execution import AgentExecution
from src.utils.logger import get_logger

log = get_logger(__name__)


class AgentExecutionRepository:
    """Repository for agent execution state persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_state(
        self,
        session_id: str,
        state_snapshot: dict,
        status: str = "running",
        iteration: int = 0,
        pause_reason: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> AgentExecution:
        """
        Save an agent execution state.

        Args:
            session_id: Session identifier
            state_snapshot: Full state snapshot as dict
            status: Execution status
            iteration: Current iteration number
            pause_reason: Reason for pause (if paused)
            error_message: Error message (if failed)

        Returns:
            Created AgentExecution instance
        """
        execution = AgentExecution(
            session_id=session_id,
            state_snapshot=state_snapshot,
            status=status,
            iteration=iteration,
            pause_reason=pause_reason,
            error_message=error_message,
        )
        self.session.add(execution)
        await self.session.commit()
        await self.session.refresh(execution)

        log.debug(
            "execution state saved",
            execution_id=str(execution.id),
            session_id=session_id,
            status=status,
        )
        return execution

    async def load_state(self, execution_id: UUID) -> Optional[AgentExecution]:
        """
        Load an execution state by ID.

        Args:
            execution_id: Execution UUID

        Returns:
            AgentExecution if found, None otherwise
        """
        result = await self.session.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def load_latest_paused(self, session_id: str) -> Optional[AgentExecution]:
        """
        Load the latest paused execution for a session.

        Args:
            session_id: Session identifier

        Returns:
            Latest paused AgentExecution if found, None otherwise
        """
        result = await self.session.execute(
            select(AgentExecution)
            .where(
                AgentExecution.session_id == session_id,
                AgentExecution.status == "paused",
            )
            .order_by(desc(AgentExecution.updated_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        execution_id: UUID,
        status: str,
        state_snapshot: Optional[dict] = None,
        pause_reason: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[AgentExecution]:
        """
        Update execution status and optionally the state snapshot.

        Args:
            execution_id: Execution UUID
            status: New status
            state_snapshot: Optional new state snapshot
            pause_reason: Reason for pause (if pausing)
            error_message: Error message (if failing)

        Returns:
            Updated AgentExecution if found, None otherwise
        """
        result = await self.session.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            log.warning("execution not found for update", execution_id=str(execution_id))
            return None

        execution.status = status
        if state_snapshot is not None:
            execution.state_snapshot = state_snapshot
        if pause_reason is not None:
            execution.pause_reason = pause_reason
        if error_message is not None:
            execution.error_message = error_message

        await self.session.commit()
        await self.session.refresh(execution)

        log.debug(
            "execution status updated",
            execution_id=str(execution_id),
            status=status,
        )
        return execution

    async def get_by_session(
        self, session_id: str, limit: int = 10
    ) -> List[AgentExecution]:
        """
        Get executions for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of executions to return

        Returns:
            List of AgentExecution in descending order by created_at
        """
        result = await self.session.execute(
            select(AgentExecution)
            .where(AgentExecution.session_id == session_id)
            .order_by(desc(AgentExecution.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, execution_id: UUID) -> bool:
        """
        Delete an execution.

        Args:
            execution_id: Execution UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if execution:
            await self.session.delete(execution)
            await self.session.commit()
            log.info("execution deleted", execution_id=str(execution_id))
            return True

        return False

    async def cleanup_old_executions(
        self, session_id: str, keep_count: int = 5
    ) -> int:
        """
        Clean up old executions for a session, keeping the most recent ones.

        Args:
            session_id: Session identifier
            keep_count: Number of recent executions to keep

        Returns:
            Number of executions deleted
        """
        # Get all executions for the session
        result = await self.session.execute(
            select(AgentExecution)
            .where(AgentExecution.session_id == session_id)
            .order_by(desc(AgentExecution.created_at))
        )
        executions = list(result.scalars().all())

        # Delete older ones
        deleted_count = 0
        for execution in executions[keep_count:]:
            await self.session.delete(execution)
            deleted_count += 1

        if deleted_count > 0:
            await self.session.commit()
            log.info(
                "old executions cleaned up",
                session_id=session_id,
                deleted=deleted_count,
            )

        return deleted_count
