"""Celery application configuration for background task processing."""

from celery import Celery
from celery.schedules import crontab
from src.config import get_settings

settings = get_settings()


def parse_cron(cron_expr: str) -> dict:
    """Parse cron expression to celery crontab kwargs.

    Expected format: "minute hour day_of_month month day_of_week"
    Example: "0 2 * * *" -> minute=0, hour=2
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}")

    minute, hour, day_of_month, month_of_year, day_of_week = parts

    return {
        "minute": minute,
        "hour": hour,
        "day_of_month": day_of_month,
        "month_of_year": month_of_year,
        "day_of_week": day_of_week,
    }


celery_app = Celery(
    "jirehs_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_timeout,
    worker_prefetch_multiplier=1,  # Fair task distribution
    task_acks_late=True,  # Re-queue on worker crash
    result_expires=86400,  # Results expire after 24 hours
)

# Auto-discover tasks from src.tasks module
celery_app.autodiscover_tasks(["src.tasks"])

# Configure beat schedule from settings
celery_app.conf.beat_schedule = {
    "daily-ingest": {
        "task": "src.tasks.scheduled_tasks.daily_ingest_task",
        "schedule": crontab(**parse_cron(settings.ingest_schedule_cron)),
    },
    "weekly-report": {
        "task": "src.tasks.report_tasks.generate_report_task",
        "schedule": crontab(**parse_cron(settings.report_schedule_cron)),
    },
    "daily-cleanup": {
        "task": "src.tasks.cleanup_tasks.cleanup_task",
        "schedule": crontab(**parse_cron(settings.cleanup_schedule_cron)),
    },
}
