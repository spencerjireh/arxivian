"""Tests for paper-scoped streaming (SPE-277): scope resolution on POST /api/v1/stream."""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.schemas.stream import DoneEventData, StreamEvent, StreamEventType
from src.services.agent_service.context import ScopedPaper


def _paper(processed=True):
    paper = Mock()
    paper.id = uuid.uuid4()
    paper.arxiv_id = "2301.00001"
    paper.title = "Attention"
    paper.pdf_processed = processed
    return paper


def _conversation(paper_id):
    conv = Mock()
    conv.paper_id = paper_id
    return conv


@pytest.fixture
def scoped_client(
    mock_db_session, mock_settings, mock_user, mock_paper_repo, mock_conversation_repo
):
    """TestClient where get_agent_service records its kwargs."""
    from src.main import app
    from src.database import get_db
    from src.config import get_settings
    from src.dependencies import (
        get_current_user_required,
        get_tier_policy,
        enforce_chat_limit,
        get_redis,
        get_usage_counter_repository,
        get_conversation_repository,
        get_paper_repository,
    )
    from src.tiers import get_policy

    captured: dict = {}

    def mock_get_agent_service(**kwargs):
        captured.update(kwargs)
        service = Mock()

        async def ask_stream(query, session_id=None):
            yield StreamEvent(event=StreamEventType.DONE, data=DoneEventData())

        service.ask_stream = ask_stream
        return service

    usage_repo = AsyncMock()
    usage_repo.increment_query_count = AsyncMock()

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_current_user_required] = lambda: mock_user
    app.dependency_overrides[get_tier_policy] = lambda: get_policy(mock_user)
    app.dependency_overrides[enforce_chat_limit] = lambda: None
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_usage_counter_repository] = lambda: usage_repo
    app.dependency_overrides[get_conversation_repository] = lambda: mock_conversation_repo
    app.dependency_overrides[get_paper_repository] = lambda: mock_paper_repo

    with patch("src.routers.stream.get_agent_service", mock_get_agent_service):
        from fastapi.testclient import TestClient

        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, captured

    app.dependency_overrides.clear()


@pytest.mark.api
class TestScopedStream:
    def test_unscoped_request_passes_no_scope(self, scoped_client):
        client, captured = scoped_client
        resp = client.post("/api/v1/stream", json={"query": "hi"})
        assert resp.status_code == 200
        assert captured["scoped_paper"] is None

    def test_arxiv_id_scopes_a_new_session(self, scoped_client, mock_paper_repo):
        client, captured = scoped_client
        paper = _paper()
        mock_paper_repo.get_by_arxiv_id.return_value = paper
        resp = client.post("/api/v1/stream", json={"query": "explain", "arxiv_id": "2301.00001"})
        assert resp.status_code == 200
        assert captured["scoped_paper"] == ScopedPaper(
            paper_id=str(paper.id), arxiv_id="2301.00001", title="Attention"
        )

    def test_unknown_or_unprocessed_paper_is_409(self, scoped_client, mock_paper_repo):
        client, captured = scoped_client
        mock_paper_repo.get_by_arxiv_id.return_value = None
        resp = client.post("/api/v1/stream", json={"query": "explain", "arxiv_id": "2301.00001"})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PAPER_NOT_INGESTED"

        mock_paper_repo.get_by_arxiv_id.return_value = _paper(processed=False)
        resp = client.post("/api/v1/stream", json={"query": "explain", "arxiv_id": "2301.00001"})
        assert resp.status_code == 409
        assert "scoped_paper" not in captured

    def test_persisted_scope_applies_without_arxiv_id(
        self, scoped_client, mock_paper_repo, mock_conversation_repo
    ):
        client, captured = scoped_client
        paper = _paper()
        mock_conversation_repo.get_by_session_id.return_value = _conversation(paper.id)
        mock_paper_repo.get_by_id.return_value = paper
        resp = client.post("/api/v1/stream", json={"query": "more", "session_id": "s1"})
        assert resp.status_code == 200
        assert captured["scoped_paper"].arxiv_id == "2301.00001"
        mock_paper_repo.get_by_id.assert_awaited_once_with(str(paper.id))

    def test_mismatched_scope_is_409(self, scoped_client, mock_paper_repo, mock_conversation_repo):
        client, _ = scoped_client
        mock_conversation_repo.get_by_session_id.return_value = _conversation(uuid.uuid4())
        mock_paper_repo.get_by_arxiv_id.return_value = _paper()
        resp = client.post(
            "/api/v1/stream", json={"query": "more", "session_id": "s1", "arxiv_id": "2301.00001"}
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SCOPE_MISMATCH"


@pytest.mark.api
class TestConversationScopeFilter:
    def test_filter_by_arxiv_id_and_items_carry_scope(
        self, client, mock_conversation_repo, mock_paper_repo, sample_conversation, mock_user
    ):
        paper = _paper()
        sample_conversation.paper_id = paper.id
        mock_paper_repo.get_by_arxiv_id.return_value = paper
        mock_paper_repo.get_by_ids.return_value = [paper]
        mock_conversation_repo.get_all.return_value = ([sample_conversation], 1)

        resp = client.get("/api/v1/conversations?arxiv_id=2301.00001")
        assert resp.status_code == 200
        assert resp.json()["conversations"][0]["arxiv_id"] == "2301.00001"
        mock_conversation_repo.get_all.assert_awaited_once_with(
            offset=0, limit=20, user_id=mock_user.id, paper_id=paper.id
        )

    def test_unknown_paper_filter_is_404(self, client, mock_paper_repo):
        mock_paper_repo.get_by_arxiv_id.return_value = None
        assert client.get("/api/v1/conversations?arxiv_id=9999.99999").status_code == 404

    def test_detail_carries_scope(
        self, client, mock_conversation_repo, mock_paper_repo, sample_conversation
    ):
        paper = _paper()
        sample_conversation.paper_id = paper.id
        mock_conversation_repo.get_with_turns.return_value = sample_conversation
        mock_paper_repo.get_by_id.return_value = paper
        resp = client.get("/api/v1/conversations/test-session-123")
        assert resp.status_code == 200
        assert resp.json()["arxiv_id"] == "2301.00001"
