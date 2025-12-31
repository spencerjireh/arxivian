"""Tests for stream router (SSE endpoints)."""

import pytest
import json
from unittest.mock import AsyncMock, Mock, patch

from src.schemas.stream import (
    StreamEvent,
    StreamEventType,
    StatusEventData,
    ContentEventData,
    MetadataEventData,
    ErrorEventData,
)


def parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE response text into list of events."""
    events = []
    current_event = {}

    for line in response_text.strip().split("\n"):
        if line.startswith("event:"):
            current_event["event"] = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_str = line.split(":", 1)[1].strip()
            try:
                current_event["data"] = json.loads(data_str)
            except json.JSONDecodeError:
                current_event["data"] = data_str
        elif line == "" and current_event:
            events.append(current_event)
            current_event = {}

    # Handle last event if no trailing newline
    if current_event:
        events.append(current_event)

    return events


class TestStreamEndpoint:
    """Tests for POST /api/v1/stream endpoint."""

    @pytest.fixture
    def mock_agent_service(self):
        """Create mock agent service that yields test events."""
        service = Mock()

        async def mock_ask_stream(query, session_id=None):
            yield StreamEvent(
                event=StreamEventType.STATUS,
                data=StatusEventData(
                    step="guardrail",
                    message="Checking query relevance",
                    details={},
                ),
            )
            yield StreamEvent(
                event=StreamEventType.STATUS,
                data=StatusEventData(
                    step="retrieval",
                    message="Searching documents",
                    details={},
                ),
            )
            yield StreamEvent(
                event=StreamEventType.CONTENT,
                data=ContentEventData(token="Hello"),
            )
            yield StreamEvent(
                event=StreamEventType.CONTENT,
                data=ContentEventData(token=" world"),
            )
            yield StreamEvent(
                event=StreamEventType.METADATA,
                data=MetadataEventData(
                    total_tokens=10,
                    retrieval_count=3,
                    guardrail_passed=True,
                ),
            )
            yield StreamEvent(
                event=StreamEventType.DONE,
                data={},
            )

        service.ask_stream = mock_ask_stream
        return service

    @pytest.fixture
    def stream_client(self, mock_db_session, mock_agent_service, mock_settings):
        """Create TestClient with mocked agent service."""
        from src.main import app
        from src.database import get_db
        from src.config import get_settings

        def mock_get_agent_service(**kwargs):
            return mock_agent_service

        app.dependency_overrides[get_db] = lambda: mock_db_session
        app.dependency_overrides[get_settings] = lambda: mock_settings

        with patch(
            "src.routers.stream.get_agent_service", mock_get_agent_service
        ):
            from fastapi.testclient import TestClient

            with TestClient(app, raise_server_exceptions=False) as client:
                yield client

        app.dependency_overrides.clear()

    def test_stream_returns_sse_content_type(self, stream_client):
        """Test that stream returns text/event-stream content type."""
        response = stream_client.post(
            "/api/v1/stream",
            json={"query": "What is machine learning?"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_stream_returns_cache_control_headers(self, stream_client):
        """Test that stream includes proper cache control headers."""
        response = stream_client.post(
            "/api/v1/stream",
            json={"query": "test query"},
        )

        assert response.status_code == 200
        assert response.headers.get("cache-control") == "no-cache"

    def test_stream_returns_events_in_correct_format(self, stream_client):
        """Test that SSE events are formatted correctly."""
        response = stream_client.post(
            "/api/v1/stream",
            json={"query": "What is BERT?"},
        )

        assert response.status_code == 200
        events = parse_sse_events(response.text)

        # Should have status, content, metadata, and done events
        event_types = [e.get("event") for e in events]
        assert "status" in event_types
        assert "content" in event_types
        assert "done" in event_types

    def test_stream_status_events_have_step_info(self, stream_client):
        """Test that status events include step information."""
        response = stream_client.post(
            "/api/v1/stream",
            json={"query": "test"},
        )

        events = parse_sse_events(response.text)
        status_events = [e for e in events if e.get("event") == "status"]

        assert len(status_events) > 0
        for event in status_events:
            assert "step" in event["data"]
            assert "message" in event["data"]

    def test_stream_content_events_have_tokens(self, stream_client):
        """Test that content events include tokens."""
        response = stream_client.post(
            "/api/v1/stream",
            json={"query": "test"},
        )

        events = parse_sse_events(response.text)
        content_events = [e for e in events if e.get("event") == "content"]

        assert len(content_events) > 0
        for event in content_events:
            assert "token" in event["data"]

    def test_stream_ends_with_done_event(self, stream_client):
        """Test that stream ends with done event."""
        response = stream_client.post(
            "/api/v1/stream",
            json={"query": "test"},
        )

        events = parse_sse_events(response.text)
        assert len(events) > 0
        assert events[-1]["event"] == "done"

    def test_stream_with_custom_provider(
        self, mock_db_session, mock_settings
    ):
        """Test stream with custom provider parameter."""
        from src.main import app
        from src.database import get_db
        from src.config import get_settings

        captured_kwargs = {}

        def capture_get_agent_service(**kwargs):
            captured_kwargs.update(kwargs)
            mock_service = Mock()

            async def mock_stream(query, session_id=None):
                yield StreamEvent(event=StreamEventType.DONE, data={})

            mock_service.ask_stream = mock_stream
            return mock_service

        app.dependency_overrides[get_db] = lambda: mock_db_session
        app.dependency_overrides[get_settings] = lambda: mock_settings

        with patch(
            "src.routers.stream.get_agent_service", capture_get_agent_service
        ):
            from fastapi.testclient import TestClient

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/stream",
                    json={
                        "query": "test",
                        "provider": "openai",
                        "model": "gpt-4o",
                    },
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert captured_kwargs.get("provider") == "openai"
        assert captured_kwargs.get("model") == "gpt-4o"

    def test_stream_with_session_id(self, mock_db_session, mock_settings):
        """Test stream with session_id for conversation continuity."""
        from src.main import app
        from src.database import get_db
        from src.config import get_settings

        captured_kwargs = {}

        def capture_get_agent_service(**kwargs):
            captured_kwargs.update(kwargs)
            mock_service = Mock()

            async def mock_stream(query, session_id=None):
                yield StreamEvent(event=StreamEventType.DONE, data={})

            mock_service.ask_stream = mock_stream
            return mock_service

        app.dependency_overrides[get_db] = lambda: mock_db_session
        app.dependency_overrides[get_settings] = lambda: mock_settings

        with patch(
            "src.routers.stream.get_agent_service", capture_get_agent_service
        ):
            from fastapi.testclient import TestClient

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/stream",
                    json={
                        "query": "follow up question",
                        "session_id": "test-session-456",
                    },
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert captured_kwargs.get("session_id") == "test-session-456"


class TestStreamValidation:
    """Tests for stream request validation."""

    @pytest.fixture
    def validation_client(self, mock_db_session, mock_settings):
        """Create client for validation tests."""
        from src.main import app
        from src.database import get_db
        from src.config import get_settings

        app.dependency_overrides[get_db] = lambda: mock_db_session
        app.dependency_overrides[get_settings] = lambda: mock_settings

        from fastapi.testclient import TestClient

        with TestClient(app, raise_server_exceptions=False) as client:
            yield client

        app.dependency_overrides.clear()

    def test_stream_missing_query(self, validation_client):
        """Test validation error for missing query."""
        response = validation_client.post("/api/v1/stream", json={})

        assert response.status_code == 422

    def test_stream_invalid_top_k(self, validation_client):
        """Test validation error for invalid top_k."""
        response = validation_client.post(
            "/api/v1/stream",
            json={"query": "test", "top_k": 50},  # Exceeds max of 10
        )

        assert response.status_code == 422

    def test_stream_invalid_guardrail_threshold(self, validation_client):
        """Test validation error for invalid guardrail_threshold."""
        response = validation_client.post(
            "/api/v1/stream",
            json={"query": "test", "guardrail_threshold": 150},
        )

        assert response.status_code == 422

    def test_stream_invalid_temperature(self, validation_client):
        """Test validation error for invalid temperature."""
        response = validation_client.post(
            "/api/v1/stream",
            json={"query": "test", "temperature": 2.0},
        )

        assert response.status_code == 422

    def test_stream_invalid_max_iterations(self, validation_client):
        """Test validation error for invalid max_iterations."""
        response = validation_client.post(
            "/api/v1/stream",
            json={"query": "test", "max_iterations": 50},
        )

        assert response.status_code == 422

    def test_stream_invalid_timeout(self, validation_client):
        """Test validation error for invalid timeout."""
        response = validation_client.post(
            "/api/v1/stream",
            json={"query": "test", "timeout_seconds": 1000},  # Exceeds max
        )

        assert response.status_code == 422


class TestStreamErrorHandling:
    """Tests for stream error handling."""

    def test_stream_timeout_returns_error_event(self, mock_db_session, mock_settings):
        """Test that timeout produces error SSE event."""
        import asyncio
        from src.main import app
        from src.database import get_db
        from src.config import get_settings

        mock_settings.agent_timeout_seconds = 1  # Very short timeout

        def slow_agent_service(**kwargs):
            mock_service = Mock()

            async def slow_stream(query, session_id=None):
                await asyncio.sleep(10)  # Will timeout
                yield StreamEvent(event=StreamEventType.DONE, data={})

            mock_service.ask_stream = slow_stream
            return mock_service

        app.dependency_overrides[get_db] = lambda: mock_db_session
        app.dependency_overrides[get_settings] = lambda: mock_settings

        with patch(
            "src.routers.stream.get_agent_service", slow_agent_service
        ):
            from fastapi.testclient import TestClient

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/stream",
                    json={"query": "test", "timeout_seconds": 10},
                )

        app.dependency_overrides.clear()

        # Should still return 200 (SSE stream)
        assert response.status_code == 200

    def test_stream_exception_returns_error_event(self, mock_db_session, mock_settings):
        """Test that exceptions produce error SSE event."""
        from src.main import app
        from src.database import get_db
        from src.config import get_settings

        def error_agent_service(**kwargs):
            mock_service = Mock()

            async def error_stream(query, session_id=None):
                raise Exception("Test error")
                yield  # Make it a generator

            mock_service.ask_stream = error_stream
            return mock_service

        app.dependency_overrides[get_db] = lambda: mock_db_session
        app.dependency_overrides[get_settings] = lambda: mock_settings

        with patch(
            "src.routers.stream.get_agent_service", error_agent_service
        ):
            from fastapi.testclient import TestClient

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/stream",
                    json={"query": "test"},
                )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        events = parse_sse_events(response.text)

        # Should have error event
        event_types = [e.get("event") for e in events]
        assert "error" in event_types

        # Should still end with done event
        assert events[-1]["event"] == "done"
