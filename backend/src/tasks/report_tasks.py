"""Report generation background tasks."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func

from src.celery_app import celery_app
from src.config import get_settings
from src.database import AsyncSessionLocal
from src.models.paper import Paper
from src.models.conversation import Conversation, ConversationTurn
from src.models.agent_execution import AgentExecution
from src.repositories.report_repository import ReportRepository
from src.tasks.utils import run_async
from src.utils.logger import get_logger

log = get_logger(__name__)


@celery_app.task(name="src.tasks.report_tasks.generate_report_task")
def generate_report_task() -> dict[str, Any]:
    """Generate scheduled usage and health reports.

    Collects metrics from the past week and generates a summary report.
    Report content is controlled by settings (report_include_*).

    Returns:
        Dictionary with report data
    """
    settings = get_settings()
    log.info("report_task_started")

    async def _run() -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        report: dict[str, Any] = {
            "generated_at": now.isoformat(),
            "period_start": week_ago.isoformat(),
            "period_end": now.isoformat(),
        }

        async with AsyncSessionLocal() as session:
            # Usage metrics
            if settings.report_include_usage:
                # Conversation stats
                conv_count = await session.execute(
                    select(func.count(Conversation.id)).where(Conversation.created_at >= week_ago)
                )
                turn_count = await session.execute(
                    select(func.count(ConversationTurn.id)).where(
                        ConversationTurn.created_at >= week_ago
                    )
                )
                exec_count = await session.execute(
                    select(func.count(AgentExecution.id)).where(
                        AgentExecution.created_at >= week_ago
                    )
                )

                report["usage"] = {
                    "conversations_created": conv_count.scalar() or 0,
                    "conversation_turns": turn_count.scalar() or 0,
                    "agent_executions": exec_count.scalar() or 0,
                }

            # Paper metrics
            if settings.report_include_papers:
                papers_count = await session.execute(
                    select(func.count(Paper.id)).where(Paper.created_at >= week_ago)
                )
                total_papers = await session.execute(select(func.count(Paper.id)))

                report["papers"] = {
                    "papers_ingested_this_week": papers_count.scalar() or 0,
                    "total_papers": total_papers.scalar() or 0,
                }

            # Health metrics
            if settings.report_include_health:
                # Count failed agent executions
                failed_execs = await session.execute(
                    select(func.count(AgentExecution.id)).where(
                        AgentExecution.created_at >= week_ago,
                        AgentExecution.status == "failed",
                    )
                )
                total_execs = await session.execute(
                    select(func.count(AgentExecution.id)).where(
                        AgentExecution.created_at >= week_ago
                    )
                )

                total = total_execs.scalar() or 0
                failed = failed_execs.scalar() or 0
                success_rate = ((total - failed) / total * 100) if total > 0 else 100.0

                report["health"] = {
                    "agent_success_rate": round(success_rate, 2),
                    "failed_executions": failed,
                    "total_executions": total,
                }

            # Persist report to database
            report_repo = ReportRepository(session)
            await report_repo.create(
                report_type="weekly",
                period_start=week_ago,
                period_end=now,
                data=report,
            )
            await session.commit()

        return report

    result = run_async(_run())
    log.info("report_task_completed", report=result)
    return result
