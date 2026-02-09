"""Cleanup background tasks for data retention."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.celery_app import celery_app
from src.config import get_settings
from src.database import AsyncSessionLocal
from src.models.conversation import Conversation
from src.models.agent_execution import AgentExecution
from src.tasks.utils import run_async
from src.utils.logger import get_logger

log = get_logger(__name__)

BATCH_SIZE = 2000


async def _batched_delete(
    session: AsyncSession,
    model: type[Any],
    cutoff_date: datetime,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Delete records older than cutoff_date in batches.

    Commits after each batch to avoid holding long transactions.

    Returns:
        Total number of records deleted.
    """
    total_deleted = 0

    while True:
        # Select a batch of IDs to delete
        id_result = await session.execute(
            select(model.id).where(model.created_at < cutoff_date).limit(batch_size)
        )
        ids = [row[0] for row in id_result.fetchall()]

        if not ids:
            break

        await session.execute(delete(model).where(model.id.in_(ids)))
        await session.commit()
        total_deleted += len(ids)

        log.debug(
            "batch_deleted",
            model=model.__tablename__,
            batch_count=len(ids),
            total_deleted=total_deleted,
        )

    return total_deleted


@celery_app.task(name="src.tasks.cleanup_tasks.cleanup_task")
def cleanup_task() -> dict[str, Any]:
    """Clean up old data based on retention settings.

    Deletes conversations and agent executions older than the
    configured retention period in batches.

    Returns:
        Dictionary with cleanup results
    """
    settings = get_settings()
    retention_days = settings.cleanup_retention_days

    log.info("cleanup_task_started", retention_days=retention_days)

    async def _run() -> dict[str, Any]:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        results = {
            "conversations_deleted": 0,
            "agent_executions_deleted": 0,
            "cutoff_date": cutoff_date.isoformat(),
        }

        async with AsyncSessionLocal() as session:
            # Delete old conversations in batches (cascade deletes turns)
            results["conversations_deleted"] = await _batched_delete(
                session, Conversation, cutoff_date
            )

            # Delete old agent executions in batches
            results["agent_executions_deleted"] = await _batched_delete(
                session, AgentExecution, cutoff_date
            )

        return results

    result = run_async(_run())
    log.info(
        "cleanup_task_completed",
        conversations_deleted=result["conversations_deleted"],
        agent_executions_deleted=result["agent_executions_deleted"],
    )
    return result
