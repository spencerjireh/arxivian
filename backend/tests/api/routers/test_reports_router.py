"""Tests for reports router."""

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock


class TestListReports:
    """Tests for GET /api/v1/reports/ endpoint."""

    def test_list_reports_empty(self, client, mock_report_repo):
        """Test listing reports when none exist."""
        mock_report_repo.list_reports.return_value = ([], 0)

        response = client.get("/api/v1/reports/")

        assert response.status_code == 200
        data = response.json()
        assert data["reports"] == []
        assert data["total"] == 0

    def test_list_reports_returns_user_reports(self, client, mock_report_repo, mock_user):
        """Test listing reports returns reports for the user."""
        report = Mock()
        report.id = uuid.uuid4()
        report.user_id = mock_user.id
        report.report_type = "daily_ingest"
        report.period_start = datetime(2026, 2, 7, tzinfo=timezone.utc)
        report.period_end = datetime(2026, 2, 7, 23, 59, 59, tzinfo=timezone.utc)
        report.data = {"ingestions": []}
        report.created_at = datetime.now(timezone.utc)

        mock_report_repo.list_reports.return_value = ([report], 1)

        response = client.get("/api/v1/reports/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["reports"]) == 1
        assert data["reports"][0]["report_type"] == "daily_ingest"
        mock_report_repo.list_reports.assert_called_once_with(
            user_id=mock_user.id, limit=20, offset=0
        )


class TestGetReport:
    """Tests for GET /api/v1/reports/{report_id} endpoint."""

    def test_get_report_found(self, client, mock_report_repo, mock_user):
        """Test getting a specific report."""
        report_id = uuid.uuid4()
        report = Mock()
        report.id = report_id
        report.user_id = mock_user.id
        report.report_type = "daily_ingest"
        report.period_start = datetime(2026, 2, 7, tzinfo=timezone.utc)
        report.period_end = datetime(2026, 2, 7, 23, 59, 59, tzinfo=timezone.utc)
        report.data = {"ingestions": [{"search_name": "ML Papers", "query": "machine learning"}]}
        report.created_at = datetime.now(timezone.utc)

        mock_report_repo.get_by_id.return_value = report

        response = client.get(f"/api/v1/reports/{report_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["report_type"] == "daily_ingest"
        assert data["data"]["ingestions"][0]["search_name"] == "ML Papers"
        mock_report_repo.get_by_id.assert_called_once_with(report_id, user_id=mock_user.id)

    def test_get_report_not_found(self, client, mock_report_repo):
        """Test getting a non-existent report returns 404."""
        mock_report_repo.get_by_id.return_value = None
        report_id = uuid.uuid4()

        response = client.get(f"/api/v1/reports/{report_id}")

        assert response.status_code == 404
