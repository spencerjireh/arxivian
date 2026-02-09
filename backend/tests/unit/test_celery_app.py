"""Unit tests for Celery application configuration."""

import pytest


class TestParseCron:
    """Tests for the parse_cron utility function."""

    def test_parse_cron_valid_daily_expression(self):
        """Verify parsing of a daily cron expression (e.g., 2 AM daily)."""
        from src.celery_app import parse_cron

        result = parse_cron("0 2 * * *")

        assert result == {
            "minute": "0",
            "hour": "2",
            "day_of_month": "*",
            "month_of_year": "*",
            "day_of_week": "*",
        }

    def test_parse_cron_valid_weekly_expression(self):
        """Verify parsing of a weekly cron expression (e.g., Monday at 8 AM)."""
        from src.celery_app import parse_cron

        result = parse_cron("0 8 * * 1")

        assert result == {
            "minute": "0",
            "hour": "8",
            "day_of_month": "*",
            "month_of_year": "*",
            "day_of_week": "1",
        }

    def test_parse_cron_complex_expression(self):
        """Verify parsing of a more complex cron expression."""
        from src.celery_app import parse_cron

        result = parse_cron("30 14 15 6 3")

        assert result == {
            "minute": "30",
            "hour": "14",
            "day_of_month": "15",
            "month_of_year": "6",
            "day_of_week": "3",
        }

    def test_parse_cron_with_ranges(self):
        """Verify parsing of cron expression with ranges."""
        from src.celery_app import parse_cron

        result = parse_cron("0-30 9-17 * * 1-5")

        assert result == {
            "minute": "0-30",
            "hour": "9-17",
            "day_of_month": "*",
            "month_of_year": "*",
            "day_of_week": "1-5",
        }

    def test_parse_cron_invalid_format_too_few_parts(self):
        """Verify error is raised for cron expression with too few parts."""
        from src.celery_app import parse_cron

        with pytest.raises(ValueError) as exc_info:
            parse_cron("0 2 * *")

        assert "Invalid cron expression" in str(exc_info.value)

    def test_parse_cron_invalid_format_too_many_parts(self):
        """Verify error is raised for cron expression with too many parts."""
        from src.celery_app import parse_cron

        with pytest.raises(ValueError) as exc_info:
            parse_cron("0 2 * * * extra")

        assert "Invalid cron expression" in str(exc_info.value)

    def test_parse_cron_empty_string(self):
        """Verify error is raised for empty cron expression."""
        from src.celery_app import parse_cron

        with pytest.raises(ValueError) as exc_info:
            parse_cron("")

        assert "Invalid cron expression" in str(exc_info.value)


class TestCeleryAppConfiguration:
    """Tests for Celery app configuration."""

    def test_celery_app_broker_configured(self):
        """Verify the celery app has broker URL configured."""
        from src.celery_app import celery_app

        # The broker URL should be set from settings
        assert celery_app.conf.broker_url is not None

    def test_celery_app_backend_configured(self):
        """Verify the celery app has result backend configured."""
        from src.celery_app import celery_app

        # The result backend should be set from settings
        assert celery_app.conf.result_backend is not None

    def test_celery_app_serializer_is_json(self):
        """Verify the celery app uses JSON serialization."""
        from src.celery_app import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

    def test_celery_app_timezone_is_utc(self):
        """Verify the celery app uses UTC timezone."""
        from src.celery_app import celery_app

        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_celery_app_task_track_started_enabled(self):
        """Verify tasks track started state."""
        from src.celery_app import celery_app

        assert celery_app.conf.task_track_started is True

    def test_celery_app_task_acks_late_enabled(self):
        """Verify late acknowledgment is enabled for reliability."""
        from src.celery_app import celery_app

        assert celery_app.conf.task_acks_late is True

    def test_beat_schedule_contains_daily_ingest(self):
        """Verify beat schedule contains daily ingest task."""
        from src.celery_app import celery_app

        assert "daily-ingest" in celery_app.conf.beat_schedule
        daily_ingest = celery_app.conf.beat_schedule["daily-ingest"]
        assert daily_ingest["task"] == "src.tasks.scheduled_tasks.daily_ingest_task"

    def test_beat_schedule_contains_daily_cleanup(self):
        """Verify beat schedule contains daily cleanup task."""
        from src.celery_app import celery_app

        assert "daily-cleanup" in celery_app.conf.beat_schedule
        daily_cleanup = celery_app.conf.beat_schedule["daily-cleanup"]
        assert daily_cleanup["task"] == "src.tasks.cleanup_tasks.cleanup_task"

    def test_celery_app_uses_redbeat_scheduler(self):
        """Verify the celery app uses RedBeat scheduler."""
        from src.celery_app import celery_app

        assert celery_app.conf.beat_scheduler == "redbeat.RedBeatScheduler"

    def test_celery_app_has_redbeat_redis_url(self):
        """Verify the celery app has RedBeat Redis URL configured."""
        from src.celery_app import celery_app

        assert celery_app.conf.redbeat_redis_url is not None
