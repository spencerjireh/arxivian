"""Tests for conversations router."""

import pytest


class TestConversationsAuthentication:
    """Tests for conversations endpoint authentication."""

    def test_list_conversations_unauthenticated_returns_401(self, unauthenticated_client):
        """Test that unauthenticated requests return 401."""
        response = unauthenticated_client.get(
            "/api/v1/conversations", params={"arxiv_id": "2301.00001"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "MISSING_TOKEN"

    def test_get_conversation_unauthenticated_returns_401(self, unauthenticated_client):
        """Test that unauthenticated requests return 401."""
        response = unauthenticated_client.get("/api/v1/conversations/test-session")

        assert response.status_code == 401

    def test_delete_conversation_unauthenticated_returns_401(self, unauthenticated_client):
        """Test that unauthenticated requests return 401."""
        response = unauthenticated_client.delete("/api/v1/conversations/test-session")

        assert response.status_code == 401


class TestListConversationsEndpoint:
    """Tests for GET /api/v1/conversations (always scoped to one paper)."""

    @pytest.fixture(autouse=True)
    def _paper_exists(self, mock_paper_repo, sample_paper):
        mock_paper_repo.get_by_arxiv_id.return_value = sample_paper

    def test_missing_arxiv_id_is_422(self, client):
        assert client.get("/api/v1/conversations").status_code == 422

    def test_unknown_paper_is_404(self, client, mock_paper_repo):
        mock_paper_repo.get_by_arxiv_id.return_value = None
        response = client.get("/api/v1/conversations", params={"arxiv_id": "9999.99999"})
        assert response.status_code == 404

    def test_list_conversations_empty(self, client, mock_conversation_repo):
        """Test listing conversations returns empty list."""
        mock_conversation_repo.get_all.return_value = ([], 0)

        response = client.get("/api/v1/conversations", params={"arxiv_id": "2301.00001"})

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

        response = client.get("/api/v1/conversations", params={"arxiv_id": "2301.00001"})

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

        response = client.get("/api/v1/conversations", params={"arxiv_id": "2301.00001"})

        assert response.status_code == 200
        data = response.json()
        assert data["conversations"][0]["turn_count"] == 1

    def test_list_conversations_includes_last_query(
        self, client, mock_conversation_repo, sample_conversation, sample_conversation_turn
    ):
        """Test that last query preview is included."""
        sample_conversation.turns = [sample_conversation_turn]
        mock_conversation_repo.get_all.return_value = ([sample_conversation], 1)

        response = client.get("/api/v1/conversations", params={"arxiv_id": "2301.00001"})

        assert response.status_code == 200
        data = response.json()
        assert data["conversations"][0]["last_query"] == "What is machine learning?"

    def test_list_conversations_pagination(self, client, mock_conversation_repo):
        """Test pagination parameters."""
        mock_conversation_repo.get_all.return_value = ([], 100)

        response = client.get("/api/v1/conversations?arxiv_id=2301.00001&offset=10&limit=50")

        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 10
        assert data["limit"] == 50

    def test_list_conversations_invalid_limit(self, client):
        """Test validation error for invalid limit."""
        response = client.get("/api/v1/conversations?arxiv_id=2301.00001&limit=200")

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
        assert "not found" in response.json()["error"]["message"].lower()

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

    def test_delete_conversation_success(self, client, mock_conversation_repo, sample_conversation):
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
        assert "not found" in response.json()["error"]["message"].lower()

    def test_delete_conversation_calls_repository_with_user_id(
        self, client, mock_conversation_repo, sample_conversation, mock_user
    ):
        """Test that delete is called on repository with user_id for ownership."""
        mock_conversation_repo.get_by_session_id.return_value = sample_conversation
        mock_conversation_repo.get_turn_count.return_value = 3

        response = client.delete("/api/v1/conversations/test-session-123")

        assert response.status_code == 200
        # Verify get_turn_count is scoped to user
        mock_conversation_repo.get_turn_count.assert_called_once_with(
            "test-session-123", user_id=mock_user.id
        )
        # Verify delete is called with user_id for ownership verification
        mock_conversation_repo.delete.assert_called_once_with(
            "test-session-123", user_id=mock_user.id
        )
        # Verify get_by_session_id was called with ownership parameter
        mock_conversation_repo.get_by_session_id.assert_called_once_with(
            "test-session-123", user_id=mock_user.id
        )
