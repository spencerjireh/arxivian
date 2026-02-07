"""Unit tests for report generation background tasks."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock, AsyncMock
from contextlib import asynccontextmanager


class TestGenerateReportTask:
    """Tests for the generate_report_task."""

    @pytest.fixture
    def mock_settings_all_enabled(self):
        """Mock settings with all report sections enabled."""
        settings = Mock()
        settings.report_include_usage = True
        settings.report_include_papers = True
        settings.report_include_health = True
        return settings

    @pytest.fixture
    def mock_settings_usage_only(self):
        """Mock settings with only usage metrics enabled."""
        settings = Mock()
        settings.report_include_usage = True
        settings.report_include_papers = False
        settings.report_include_health = False
        return settings

    @pytest.fixture
    def mock_settings_all_disabled(self):
        """Mock settings with all report sections disabled."""
        settings = Mock()
        settings.report_include_usage = False
        settings.report_include_papers = False
        settings.report_include_health = False
        return settings

    def test_includes_usage_metrics_when_enabled(self, mock_settings_all_enabled):
        """Verify usage metrics are included when setting is enabled."""
        from src.tasks.report_tasks import generate_report_task

        mock_session = AsyncMock()

        # Mock query results for usage metrics
        conv_result = Mock()
        conv_result.scalar.return_value = 100

        turn_result = Mock()
        turn_result.scalar.return_value = 500

        exec_result = Mock()
        exec_result.scalar.return_value = 200

        paper_result = Mock()
        paper_result.scalar.return_value = 50

        total_paper_result = Mock()
        total_paper_result.scalar.return_value = 1000

        failed_exec_result = Mock()
        failed_exec_result.scalar.return_value = 10

        total_exec_result = Mock()
        total_exec_result.scalar.return_value = 200

        mock_session.execute = AsyncMock(
            side_effect=[
                conv_result,
                turn_result,
                exec_result,
                paper_result,
                total_paper_result,
                failed_exec_result,
                total_exec_result,
            ]
        )
        mock_session.commit = AsyncMock()

        mock_report_repo = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.report_tasks.get_settings", return_value=mock_settings_all_enabled):
            with patch("src.tasks.report_tasks.AsyncSessionLocal", mock_session_ctx):
                with patch(
                    "src.tasks.report_tasks.ReportRepository", return_value=mock_report_repo
                ):
                    result = generate_report_task()

        assert "usage" in result
        assert result["usage"]["conversations_created"] == 100
        assert result["usage"]["conversation_turns"] == 500
        assert result["usage"]["agent_executions"] == 200

    def test_excludes_usage_metrics_when_disabled(self, mock_settings_all_disabled):
        """Verify usage metrics are excluded when setting is disabled."""
        from src.tasks.report_tasks import generate_report_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_report_repo = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.report_tasks.get_settings", return_value=mock_settings_all_disabled):
            with patch("src.tasks.report_tasks.AsyncSessionLocal", mock_session_ctx):
                with patch(
                    "src.tasks.report_tasks.ReportRepository", return_value=mock_report_repo
                ):
                    result = generate_report_task()

        assert "usage" not in result

    def test_includes_paper_metrics_when_enabled(self, mock_settings_all_enabled):
        """Verify paper metrics are included when setting is enabled."""
        from src.tasks.report_tasks import generate_report_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock all query results
        count_result = Mock()
        count_result.scalar.return_value = 50

        mock_session.execute = AsyncMock(return_value=count_result)

        mock_report_repo = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.report_tasks.get_settings", return_value=mock_settings_all_enabled):
            with patch("src.tasks.report_tasks.AsyncSessionLocal", mock_session_ctx):
                with patch(
                    "src.tasks.report_tasks.ReportRepository", return_value=mock_report_repo
                ):
                    result = generate_report_task()

        assert "papers" in result
        assert "papers_ingested_this_week" in result["papers"]
        assert "total_papers" in result["papers"]

    def test_includes_health_metrics_when_enabled(self, mock_settings_all_enabled):
        """Verify health metrics are included when setting is enabled."""
        from src.tasks.report_tasks import generate_report_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock all query results
        count_result = Mock()
        count_result.scalar.return_value = 100

        mock_session.execute = AsyncMock(return_value=count_result)

        mock_report_repo = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.report_tasks.get_settings", return_value=mock_settings_all_enabled):
            with patch("src.tasks.report_tasks.AsyncSessionLocal", mock_session_ctx):
                with patch(
                    "src.tasks.report_tasks.ReportRepository", return_value=mock_report_repo
                ):
                    result = generate_report_task()

        assert "health" in result
        assert "agent_success_rate" in result["health"]
        assert "failed_executions" in result["health"]
        assert "total_executions" in result["health"]

    def test_calculates_success_rate_correctly(self, mock_settings_all_enabled):
        """Verify success rate calculation is correct."""
        from src.tasks.report_tasks import generate_report_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Create result sequence for all queries
        results = []

        # Usage: conv, turn, exec
        for _ in range(3):
            r = Mock()
            r.scalar.return_value = 10
            results.append(r)

        # Papers: week papers, total papers
        for _ in range(2):
            r = Mock()
            r.scalar.return_value = 20
            results.append(r)

        # Health: failed execs = 10, total execs = 100
        failed_r = Mock()
        failed_r.scalar.return_value = 10
        results.append(failed_r)

        total_r = Mock()
        total_r.scalar.return_value = 100
        results.append(total_r)

        mock_session.execute = AsyncMock(side_effect=results)

        mock_report_repo = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.report_tasks.get_settings", return_value=mock_settings_all_enabled):
            with patch("src.tasks.report_tasks.AsyncSessionLocal", mock_session_ctx):
                with patch(
                    "src.tasks.report_tasks.ReportRepository", return_value=mock_report_repo
                ):
                    result = generate_report_task()

        # 90 successful out of 100 = 90%
        assert result["health"]["agent_success_rate"] == 90.0
        assert result["health"]["failed_executions"] == 10
        assert result["health"]["total_executions"] == 100

    def test_success_rate_100_when_no_failures(self, mock_settings_all_enabled):
        """Verify success rate is 100% when no failures."""
        from src.tasks.report_tasks import generate_report_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Create result sequence
        results = []

        # Usage queries
        for _ in range(3):
            r = Mock()
            r.scalar.return_value = 10
            results.append(r)

        # Paper queries
        for _ in range(2):
            r = Mock()
            r.scalar.return_value = 20
            results.append(r)

        # Health: 0 failed, 50 total
        failed_r = Mock()
        failed_r.scalar.return_value = 0
        results.append(failed_r)

        total_r = Mock()
        total_r.scalar.return_value = 50
        results.append(total_r)

        mock_session.execute = AsyncMock(side_effect=results)

        mock_report_repo = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.report_tasks.get_settings", return_value=mock_settings_all_enabled):
            with patch("src.tasks.report_tasks.AsyncSessionLocal", mock_session_ctx):
                with patch(
                    "src.tasks.report_tasks.ReportRepository", return_value=mock_report_repo
                ):
                    result = generate_report_task()

        assert result["health"]["agent_success_rate"] == 100.0

    def test_success_rate_100_when_no_executions(self, mock_settings_all_enabled):
        """Verify success rate is 100% when no executions (edge case)."""
        from src.tasks.report_tasks import generate_report_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Create result sequence
        results = []

        # Usage queries
        for _ in range(3):
            r = Mock()
            r.scalar.return_value = 0
            results.append(r)

        # Paper queries
        for _ in range(2):
            r = Mock()
            r.scalar.return_value = 0
            results.append(r)

        # Health: 0 failed, 0 total
        failed_r = Mock()
        failed_r.scalar.return_value = 0
        results.append(failed_r)

        total_r = Mock()
        total_r.scalar.return_value = 0
        results.append(total_r)

        mock_session.execute = AsyncMock(side_effect=results)

        mock_report_repo = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.report_tasks.get_settings", return_value=mock_settings_all_enabled):
            with patch("src.tasks.report_tasks.AsyncSessionLocal", mock_session_ctx):
                with patch(
                    "src.tasks.report_tasks.ReportRepository", return_value=mock_report_repo
                ):
                    result = generate_report_task()

        # Should be 100% when total is 0 (avoid division by zero)
        assert result["health"]["agent_success_rate"] == 100.0

    def test_report_includes_period_timestamps(self, mock_settings_all_disabled):
        """Verify report includes generated_at and period timestamps."""
        from src.tasks.report_tasks import generate_report_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_report_repo = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.report_tasks.get_settings", return_value=mock_settings_all_disabled):
            with patch("src.tasks.report_tasks.AsyncSessionLocal", mock_session_ctx):
                with patch(
                    "src.tasks.report_tasks.ReportRepository", return_value=mock_report_repo
                ):
                    result = generate_report_task()

        assert "generated_at" in result
        assert "period_start" in result
        assert "period_end" in result

        # Verify timestamps are valid ISO format
        generated_at = datetime.fromisoformat(result["generated_at"])
        period_start = datetime.fromisoformat(result["period_start"])
        period_end = datetime.fromisoformat(result["period_end"])

        # Period should be approximately 7 days
        delta = period_end - period_start
        assert 6 <= delta.days <= 7

    def test_report_period_is_last_week(self, mock_settings_all_disabled):
        """Verify report period covers the last 7 days."""
        from src.tasks.report_tasks import generate_report_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_report_repo = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.report_tasks.get_settings", return_value=mock_settings_all_disabled):
            with patch("src.tasks.report_tasks.AsyncSessionLocal", mock_session_ctx):
                with patch(
                    "src.tasks.report_tasks.ReportRepository", return_value=mock_report_repo
                ):
                    result = generate_report_task()

        period_start = datetime.fromisoformat(result["period_start"])
        period_end = datetime.fromisoformat(result["period_end"])

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        # Allow 1 minute tolerance
        assert abs((period_end - now).total_seconds()) < 60
        assert abs((period_start - week_ago).total_seconds()) < 60

    def test_persists_report_to_database(self, mock_settings_all_disabled):
        """Verify report is persisted via ReportRepository."""
        from src.tasks.report_tasks import generate_report_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_report_repo = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.report_tasks.get_settings", return_value=mock_settings_all_disabled):
            with patch("src.tasks.report_tasks.AsyncSessionLocal", mock_session_ctx):
                with patch(
                    "src.tasks.report_tasks.ReportRepository", return_value=mock_report_repo
                ):
                    result = generate_report_task()

        # Verify repo.create was called once with correct args
        mock_report_repo.create.assert_called_once()
        call_kwargs = mock_report_repo.create.call_args.kwargs
        assert call_kwargs["report_type"] == "weekly"
        assert "period_start" in call_kwargs
        assert "period_end" in call_kwargs
        assert "data" in call_kwargs

        # Verify session.commit was called
        mock_session.commit.assert_called_once()
