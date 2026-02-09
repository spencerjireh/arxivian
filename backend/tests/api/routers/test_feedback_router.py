"""Tests for feedback router."""

from unittest.mock import Mock, patch


class TestFeedbackEndpoint:
    """Tests for POST /api/v1/feedback endpoint."""

    def test_feedback_success(self, client):
        """Test successful feedback submission."""
        with patch("src.clients.langfuse_utils.get_langfuse") as mock_get_langfuse:
            mock_langfuse = Mock()
            mock_get_langfuse.return_value = mock_langfuse

            response = client.post(
                "/api/v1/feedback",
                json={
                    "trace_id": "trace-123",
                    "score": 1,
                    "comment": "Great answer!",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify Langfuse score was called
            mock_langfuse.score.assert_called_once_with(
                trace_id="trace-123",
                name="user-feedback",
                value=1,
                comment="Great answer!",
            )

    def test_feedback_without_comment(self, client):
        """Test feedback submission without comment."""
        with patch("src.clients.langfuse_utils.get_langfuse") as mock_get_langfuse:
            mock_langfuse = Mock()
            mock_get_langfuse.return_value = mock_langfuse

            response = client.post(
                "/api/v1/feedback",
                json={
                    "trace_id": "trace-123",
                    "score": 0,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_feedback_langfuse_not_enabled(self, client):
        """Test feedback when Langfuse is not enabled."""
        with patch("src.clients.langfuse_utils.get_langfuse") as mock_get_langfuse:
            mock_get_langfuse.return_value = None

            response = client.post(
                "/api/v1/feedback",
                json={
                    "trace_id": "trace-123",
                    "score": 1,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "not enabled" in data["message"]

    def test_feedback_langfuse_error(self, client):
        """Test feedback when Langfuse throws an error."""
        with patch("src.clients.langfuse_utils.get_langfuse") as mock_get_langfuse:
            mock_langfuse = Mock()
            mock_langfuse.score.side_effect = Exception("Langfuse error")
            mock_get_langfuse.return_value = mock_langfuse

            response = client.post(
                "/api/v1/feedback",
                json={
                    "trace_id": "trace-123",
                    "score": 1,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Failed to submit feedback" in data["message"]

    def test_feedback_missing_trace_id(self, client):
        """Test validation error for missing trace_id."""
        response = client.post(
            "/api/v1/feedback",
            json={"score": 1},
        )

        assert response.status_code == 422

    def test_feedback_missing_score(self, client):
        """Test validation error for missing score."""
        response = client.post(
            "/api/v1/feedback",
            json={"trace_id": "trace-123"},
        )

        assert response.status_code == 422

    def test_feedback_score_out_of_range_high(self, client):
        """Test validation error for score > 1."""
        response = client.post(
            "/api/v1/feedback",
            json={"trace_id": "trace-123", "score": 2},
        )

        assert response.status_code == 422

    def test_feedback_score_out_of_range_low(self, client):
        """Test validation error for score < 0."""
        response = client.post(
            "/api/v1/feedback",
            json={"trace_id": "trace-123", "score": -1},
        )

        assert response.status_code == 422

    def test_feedback_comment_max_length(self, client):
        """Test validation error for comment exceeding max length."""
        response = client.post(
            "/api/v1/feedback",
            json={
                "trace_id": "trace-123",
                "score": 1,
                "comment": "A" * 1001,  # Exceeds 1000 char limit
            },
        )

        assert response.status_code == 422
