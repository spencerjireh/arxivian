"""Tests for conversations router."""

import pytest
from unittest.mock import Mock, patch


class TestListConversationsEndpoint:
    """Tests for GET /api/v1/conversations endpoint."""

    def test_list_conversations_empty(self, client, mock_conversation_repo):
        """Test listing conversations returns empty list."""
        mock_conversation_repo.get_all.return_value = ([], 0)

        response = client.get("/api/v1/conversations")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["conversations"] == []
        assert data["offset"] == 0
        assert data["limit"] == 20

    def test_list_conversations_with_results(
        self, client, mock_conversation_repo, sample_conversation
    ):
        """Test listing conversations returns results."""
        mock_conversation_repo.get_all.return_value = ([sample_conversation], 1)

        response = client.get("/api/v1/conversations")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["session_id"] == "test-session-123"

    def test_list_conversations_includes_turn_count(
        self, client, mock_conversation_repo, sample_conversation, sample_conversation_turn
    ):
        """Test that turn count is included."""
        sample_conversation.turns = [sample_conversation_turn]
        mock_conversation_repo.get_all.return_value = ([sample_conversation], 1)

        response = client.get("/api/v1/conversations")

        assert response.status_code == 200
        data = response.json()
        assert data["conversations"][0]["turn_count"] == 1

    def test_list_conversations_includes_last_query(
        self, client, mock_conversation_repo, sample_conversation, sample_conversation_turn
    ):
        """Test that last query preview is included."""
        sample_conversation.turns = [sample_conversation_turn]
        mock_conversation_repo.get_all.return_value = ([sample_conversation], 1)

        response = client.get("/api/v1/conversations")

        assert response.status_code == 200
        data = response.json()
        assert data["conversations"][0]["last_query"] == "What is machine learning?"

    def test_list_conversations_pagination(self, client, mock_conversation_repo):
        """Test pagination parameters."""
        mock_conversation_repo.get_all.return_value = ([], 100)

        response = client.get("/api/v1/conversations?offset=10&limit=50")

        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 10
        assert data["limit"] == 50

    def test_list_conversations_invalid_limit(self, client):
        """Test validation error for invalid limit."""
        response = client.get("/api/v1/conversations?limit=200")

        assert response.status_code == 422


class TestGetConversationEndpoint:
    """Tests for GET /api/v1/conversations/{session_id} endpoint."""

    def test_get_conversation_found(
        self, client, mock_conversation_repo, sample_conversation, sample_conversation_turn
    ):
        """Test getting a conversation that exists."""
        sample_conversation.turns = [sample_conversation_turn]
        mock_conversation_repo.get_with_turns.return_value = sample_conversation

        response = client.get("/api/v1/conversations/test-session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert len(data["turns"]) == 1
        assert data["turns"][0]["user_query"] == "What is machine learning?"
        assert data["turns"][0]["agent_response"] == "Machine learning is a branch of AI."

    def test_get_conversation_not_found(self, client, mock_conversation_repo):
        """Test getting a conversation that doesn't exist."""
        mock_conversation_repo.get_with_turns.return_value = None

        response = client.get("/api/v1/conversations/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_conversation_includes_turn_metadata(
        self, client, mock_conversation_repo, sample_conversation, sample_conversation_turn
    ):
        """Test that turn metadata is included."""
        sample_conversation.turns = [sample_conversation_turn]
        mock_conversation_repo.get_with_turns.return_value = sample_conversation

        response = client.get("/api/v1/conversations/test-session-123")

        assert response.status_code == 200
        data = response.json()
        turn = data["turns"][0]
        assert turn["provider"] == "openai"
        assert turn["model"] == "gpt-4o-mini"
        assert turn["guardrail_score"] == 85
        assert turn["retrieval_attempts"] == 1


class TestDeleteConversationEndpoint:
    """Tests for DELETE /api/v1/conversations/{session_id} endpoint."""

    def test_delete_conversation_success(
        self, client, mock_conversation_repo, sample_conversation
    ):
        """Test successful conversation deletion."""
        mock_conversation_repo.get_by_session_id.return_value = sample_conversation
        mock_conversation_repo.get_turn_count.return_value = 5

        response = client.delete("/api/v1/conversations/test-session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert data["turns_deleted"] == 5

    def test_delete_conversation_not_found(self, client, mock_conversation_repo):
        """Test deleting a conversation that doesn't exist."""
        mock_conversation_repo.get_by_session_id.return_value = None
        mock_conversation_repo.get_turn_count.return_value = 0

        response = client.delete("/api/v1/conversations/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_conversation_calls_repository(
        self, client, mock_conversation_repo, sample_conversation
    ):
        """Test that delete is called on repository."""
        mock_conversation_repo.get_by_session_id.return_value = sample_conversation
        mock_conversation_repo.get_turn_count.return_value = 3

        response = client.delete("/api/v1/conversations/test-session-123")

        assert response.status_code == 200
        mock_conversation_repo.delete.assert_called_once_with("test-session-123")


class TestCancelStreamEndpoint:
    """Tests for POST /api/v1/conversations/{session_id}/cancel endpoint."""

    def test_cancel_stream_success(self, client):
        """Test successful stream cancellation."""
        from src.services.task_registry import task_registry

        # Register a mock task
        mock_task = Mock()
        task_registry.register("test-session-123", mock_task)

        response = client.post("/api/v1/conversations/test-session-123/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert data["cancelled"] is True
        assert "cancelled successfully" in data["message"]

    def test_cancel_stream_no_active_stream(self, client):
        """Test cancellation when no stream exists."""
        response = client.post("/api/v1/conversations/nonexistent/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "nonexistent"
        assert data["cancelled"] is False
        assert "No active stream" in data["message"]
