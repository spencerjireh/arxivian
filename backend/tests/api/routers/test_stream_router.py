"""Tests for POST /api/v1/stream (paper-scoped SSE endpoint)."""

import asyncio
import json
import uuid
from unittest.mock import Mock, patch

import pytest

from src.schemas.stream import (
    ContentEventData,
    DoneEventData,
    MetadataEventData,
    StatusEventData,
    StreamEvent,
    StreamEventType,
)
from src.services.agent_service.context import ScopedPaper

STREAM = "/api/v1/stream"
BODY = {"query": "explain the method", "arxiv_id": "2301.00001"}


def parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE response text into a list of {event, data} dicts."""
    events: list[dict] = []
    current: dict = {}
    for line in response_text.strip().split("\n"):
        if line.startswith("event:"):
            current["event"] = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            raw = line.split(":", 1)[1].strip()
            try:
                current["data"] = json.loads(raw)
            except json.JSONDecodeError:
                current["data"] = raw
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


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


async def _events(query, session_id=None):
    yield StreamEvent(
        event=StreamEventType.STATUS,
        data=StatusEventData(step="classifying", message="Classifying query...", details={}),
    )
    yield StreamEvent(event=StreamEventType.CONTENT, data=ContentEventData(token="Hello"))
    yield StreamEvent(event=StreamEventType.CONTENT, data=ContentEventData(token=" world"))
    yield StreamEvent(
        event=StreamEventType.METADATA,
        data=MetadataEventData(query=query, execution_time_ms=1.0, retrieval_attempts=1),
    )
    yield StreamEvent(event=StreamEventType.DONE, data=DoneEventData())


@pytest.fixture
def agent(mock_paper_repo):
    """Patch get_agent_service; returns the captured kwargs. The scoped paper exists."""
    mock_paper_repo.get_by_arxiv_id.return_value = _paper()
    captured: dict = {}

    def fake_get_agent_service(**kwargs):
        captured.update(kwargs)
        service = Mock()
        service.ask_stream = captured.pop("_stream", _events)
        return service

    with patch("src.routers.stream.get_agent_service", fake_get_agent_service):
        yield captured


@pytest.mark.api
class TestStreamEndpoint:
    def test_sse_headers(self, client, agent):
        resp = client.post(STREAM, json=BODY)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers["cache-control"] == "no-cache"

    def test_events_in_order_and_done_last(self, client, agent):
        events = parse_sse_events(client.post(STREAM, json=BODY).text)
        types = [e["event"] for e in events]
        assert types[0] == "status"
        assert types[-1] == "done"
        assert [e["data"]["token"] for e in events if e["event"] == "content"] == [
            "Hello",
            " world",
        ]
        assert events[0]["data"]["step"] == "classifying"

    def test_session_id_forwarded(self, client, agent, mock_paper_repo, mock_conversation_repo):
        mock_conversation_repo.get_by_session_id.return_value = _conversation(
            mock_paper_repo.get_by_arxiv_id.return_value.id
        )
        resp = client.post(STREAM, json={**BODY, "session_id": "s1"})
        assert resp.status_code == 200

    def test_agent_built_with_scope_only(self, client, agent, mock_user, mock_paper_repo):
        client.post(STREAM, json=BODY)
        paper = mock_paper_repo.get_by_arxiv_id.return_value
        assert agent["scoped_paper"] == ScopedPaper(
            paper_id=str(paper.id), arxiv_id="2301.00001", title="Attention"
        )
        assert agent["user_id"] == mock_user.id
        assert set(agent) == {"db_session", "user_id", "graph", "scoped_paper"}

    def test_usage_counted(self, client, agent, mock_usage_repo, mock_user):
        client.post(STREAM, json=BODY)
        mock_usage_repo.increment_query_count.assert_awaited_once_with(mock_user.id)


@pytest.mark.api
class TestScopeResolution:
    def test_unknown_or_unprocessed_paper_is_409(self, client, agent, mock_paper_repo):
        mock_paper_repo.get_by_arxiv_id.return_value = None
        resp = client.post(STREAM, json=BODY)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PAPER_NOT_INGESTED"

        mock_paper_repo.get_by_arxiv_id.return_value = _paper(processed=False)
        assert client.post(STREAM, json=BODY).status_code == 409
        assert "scoped_paper" not in agent

    def test_mismatched_scope_is_409(self, client, agent, mock_conversation_repo):
        mock_conversation_repo.get_by_session_id.return_value = _conversation(uuid.uuid4())
        resp = client.post(STREAM, json={**BODY, "session_id": "s1"})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SCOPE_MISMATCH"

    def test_unscoped_conversation_gets_scoped(self, client, agent, mock_conversation_repo):
        # A legacy thread with no paper_id accepts the first scoped turn.
        mock_conversation_repo.get_by_session_id.return_value = _conversation(None)
        assert client.post(STREAM, json={**BODY, "session_id": "s1"}).status_code == 200


@pytest.mark.api
class TestStreamValidation:
    def test_unauthenticated_is_401(self, unauthenticated_client):
        assert unauthenticated_client.post(STREAM, json=BODY).status_code == 401

    def test_empty_body_is_422(self, client):
        assert client.post(STREAM, json={}).status_code == 422

    def test_missing_arxiv_id_is_422(self, client):
        assert client.post(STREAM, json={"query": "q"}).status_code == 422

    @pytest.mark.parametrize(
        "extra", [{"model": "openai/gpt-4o"}, {"temperature": 0.9}, {"top_k": 5}, {"resume": {}}]
    )
    def test_removed_knobs_are_422(self, client, extra):
        assert client.post(STREAM, json={**BODY, **extra}).status_code == 422


@pytest.mark.api
class TestStreamErrorHandling:
    def test_timeout_yields_error_then_done(self, client, agent, mock_settings):
        mock_settings.agent_timeout_seconds = 0.05

        async def slow(query, session_id=None):
            await asyncio.sleep(1)
            yield StreamEvent(event=StreamEventType.DONE, data=DoneEventData())

        agent["_stream"] = slow
        events = parse_sse_events(client.post(STREAM, json=BODY).text)
        assert [e["event"] for e in events] == ["error", "done"]
        assert events[0]["data"]["code"] == "TIMEOUT"

    def test_exception_yields_generic_error(self, client, agent):
        async def broken(query, session_id=None):
            raise RuntimeError("boom")
            yield  # pragma: no cover

        agent["_stream"] = broken
        events = parse_sse_events(client.post(STREAM, json=BODY).text)
        assert events[0]["event"] == "error"
        assert events[0]["data"]["code"] == "INTERNAL_ERROR"
        assert "boom" not in events[0]["data"]["error"]


@pytest.mark.api
class TestConversationScope:
    def test_list_items_carry_scope(
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
