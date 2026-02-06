"""Cleanup background tasks for data retention."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select, func

from src.celery_app import celery_app
from src.config import get_settings
from src.database import AsyncSessionLocal
from src.models.conversation import Conversation
from src.models.agent_execution import AgentExecution
from src.tasks.utils import run_async
from src.utils.logger import get_logger

log = get_logger(__name__)


@celery_app.task(name="src.tasks.cleanup_tasks.cleanup_task")
def cleanup_task() -> dict[str, Any]:
    """Clean up old data based on retention settings.

    Deletes conversations and agent executions older than the
    configured retention period.

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
            # Delete old conversations (cascade deletes turns)
            conv_count_result = await session.execute(
                select(func.count(Conversation.id)).where(
                    Conversation.created_at < cutoff_date
                )
            )
            conv_count = conv_count_result.scalar() or 0

            if conv_count > 0:
                await session.execute(
                    delete(Conversation).where(Conversation.created_at < cutoff_date)
                )
                results["conversations_deleted"] = conv_count

            # Delete old agent executions
            exec_count_result = await session.execute(
                select(func.count(AgentExecution.id)).where(
                    AgentExecution.created_at < cutoff_date
                )
            )
            exec_count = exec_count_result.scalar() or 0

            if exec_count > 0:
                await session.execute(
                    delete(AgentExecution).where(AgentExecution.created_at < cutoff_date)
                )
                results["agent_executions_deleted"] = exec_count

            await session.commit()

        return results

    result = run_async(_run())
    log.info(
        "cleanup_task_completed",
        conversations_deleted=result["conversations_deleted"],
        agent_executions_deleted=result["agent_executions_deleted"],
    )
    return result
