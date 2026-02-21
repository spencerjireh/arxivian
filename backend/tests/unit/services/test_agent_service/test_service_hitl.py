"""Tests for AgentService ask_stream/resume_stream HITL two-stream flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from src.schemas.stream import StreamEventType
from src.services.agent_service.service import AgentService


def _make_llm_client(provider: str = "openai", model: str = "gpt-4o-mini"):
    client = MagicMock()
    client.provider_name = provider
    client.model = model
    return client


def _make_context_kwargs(**overrides):
    defaults = dict(
        guardrail_threshold=75,
        top_k=3,
        max_retrieval_attempts=3,
        max_iterations=5,
        temperature=0.3,
        user_id=None,
        daily_ingests=None,
        usage_counter_repo=None,
    )
    defaults.update(overrides)
    return defaults


def _make_service(
    graph_events=None,
    interrupt_value=None,
    conversation_repo=None,
    ingest_service=None,
    **ctx_overrides,
):
    """Create an AgentService with a mock graph producing given events."""
    llm_client = _make_llm_client()
    search_service = MagicMock()
    graph = AsyncMock()

    # Build the stream events the mock graph yields
    async def mock_astream(input_data, config, stream_mode=None):
        if graph_events:
            for evt in graph_events:
                yield evt
        # If interrupt_value is set, simulate an interrupt
        if interrupt_value is not None:
            intr = MagicMock()
            intr.value = interrupt_value
            yield ("updates", {"__interrupt__": [intr]})

    graph.astream = mock_astream

    service = AgentService(
        llm_client=llm_client,
        search_service=search_service,
        graph=graph,
        redis=AsyncMock(),
        ingest_service=ingest_service,
        conversation_repo=conversation_repo,
        **_make_context_kwargs(**ctx_overrides),
    )
    return service


class TestAskStreamNormal:
    """ask_stream normal flow (no interrupt)."""

    @pytest.mark.asyncio
    async def test_normal_flow_saves_turn_and_emits_metadata(self):
        """Normal flow emits METADATA + DONE and saves turn."""
        repo = AsyncMock()
        repo.get_turn_count = AsyncMock(return_value=0)
        repo.get_history = AsyncMock(return_value=[])
        saved_turn = MagicMock()
        saved_turn.turn_number = 0
        repo.save_turn = AsyncMock(return_value=saved_turn)

        service = _make_service(
            graph_events=[
                ("updates", {"generate": {"messages": []}}),
            ],
            conversation_repo=repo,
        )

        events = []
        async for event in service.ask_stream("test query", session_id="s1"):
            events.append(event)

        event_types = [e.event for e in events]
        assert StreamEventType.METADATA in event_types
        assert StreamEventType.DONE in event_types
        repo.save_turn.assert_called_once()


class TestAskStreamInterrupt:
    """ask_stream with HITL interrupt."""

    @pytest.mark.asyncio
    async def test_interrupt_emits_confirm_and_saves_pending_turn(self):
        """When graph is interrupted, emits CONFIRM_INGEST and saves partial turn."""
        repo = AsyncMock()
        repo.get_turn_count = AsyncMock(return_value=0)
        repo.get_history = AsyncMock(return_value=[])
        saved_turn = MagicMock()
        saved_turn.turn_number = 0
        repo.save_turn = AsyncMock(return_value=saved_turn)

        interrupt_data = {
            "papers": [
                {
                    "arxiv_id": "2301.00001",
                    "title": "Paper A",
                    "pdf_url": "https://arxiv.org/pdf/2301.00001.pdf",
                }
            ],
            "proposed_ids": ["2301.00001"],
        }

        service = _make_service(
            interrupt_value=interrupt_data,
            conversation_repo=repo,
        )

        events = []
        async for event in service.ask_stream("find papers", session_id="s1"):
            events.append(event)

        event_types = [e.event for e in events]
        assert StreamEventType.CONFIRM_INGEST in event_types
        assert StreamEventType.METADATA in event_types
        assert StreamEventType.DONE in event_types

        # Verify partial turn saved with pending_confirmation
        repo.save_turn.assert_called_once()
        turn_data = repo.save_turn.call_args[0][1]
        assert turn_data.pending_confirmation is not None
        assert turn_data.pending_confirmation["papers"] == interrupt_data["papers"]
        assert turn_data.agent_response == ""

        # Verify explicit commit
        repo.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_interrupt_stores_model_and_temperature_in_pending(self):
        """pending_confirmation includes model and temperature for resume."""
        repo = AsyncMock()
        repo.get_turn_count = AsyncMock(return_value=0)
        repo.get_history = AsyncMock(return_value=[])
        saved_turn = MagicMock()
        saved_turn.turn_number = 0
        repo.save_turn = AsyncMock(return_value=saved_turn)

        service = _make_service(
            interrupt_value={"papers": [], "proposed_ids": []},
            conversation_repo=repo,
        )

        events = []
        async for event in service.ask_stream("test", session_id="s1"):
            events.append(event)

        turn_data = repo.save_turn.call_args[0][1]
        assert "model" in turn_data.pending_confirmation
        assert "temperature" in turn_data.pending_confirmation
        assert turn_data.pending_confirmation["model"] == "gpt-4o-mini"
        assert turn_data.pending_confirmation["temperature"] == 0.3


class TestResumeStream:
    """resume_stream tests."""

    @pytest.mark.asyncio
    async def test_double_confirm_returns_error(self):
        """When no pending confirmation exists, emit ERROR(DOUBLE_CONFIRM)."""
        repo = AsyncMock()
        repo.get_pending_turn = AsyncMock(return_value=None)

        service = _make_service(conversation_repo=repo)

        events = []
        async for event in service.resume_stream(
            session_id="s1",
            thread_id="s1:0",
            approved=True,
            selected_ids=["2301.00001"],
        ):
            events.append(event)

        event_types = [e.event for e in events]
        assert StreamEventType.ERROR in event_types
        assert StreamEventType.DONE in event_types
        error_event = next(e for e in events if e.event == StreamEventType.ERROR)
        assert error_event.data.code == "DOUBLE_CONFIRM"

    @pytest.mark.asyncio
    async def test_approved_runs_ingest_and_resumes_graph(self):
        """Approved resume runs inline ingest and resumes graph."""
        repo = AsyncMock()
        pending_turn = MagicMock()
        pending_turn.turn_number = 0
        pending_turn.pending_confirmation = {"papers": [], "proposed_ids": []}
        repo.get_pending_turn = AsyncMock(return_value=pending_turn)
        repo.get_turn_count = AsyncMock(return_value=1)
        saved_turn = MagicMock()
        saved_turn.turn_number = 1
        repo.save_turn = AsyncMock(return_value=saved_turn)
        repo.clear_pending_confirmation = AsyncMock()

        ingest_service = AsyncMock()
        ingest_result = MagicMock()
        ingest_result.papers_processed = 1
        ingest_result.chunks_created = 10
        ingest_result.errors = []
        ingest_service.ingest_by_ids = AsyncMock(return_value=ingest_result)

        service = _make_service(
            graph_events=[
                ("updates", {"generate": {"messages": []}}),
            ],
            conversation_repo=repo,
            ingest_service=ingest_service,
        )

        events = []
        async for event in service.resume_stream(
            session_id="s1",
            thread_id="s1:0",
            approved=True,
            selected_ids=["2301.00001"],
        ):
            events.append(event)

        event_types = [e.event for e in events]
        assert StreamEventType.INGEST_COMPLETE in event_types
        assert StreamEventType.METADATA in event_types
        assert StreamEventType.DONE in event_types

        # Verify ingest was called
        ingest_service.ingest_by_ids.assert_called_once_with(["2301.00001"])

        # Verify new turn saved with synthetic query
        repo.save_turn.assert_called_once()
        turn_data = repo.save_turn.call_args[0][1]
        assert "Confirmed ingestion" in turn_data.user_query

        # Verify pending cleared
        repo.clear_pending_confirmation.assert_called_once_with("s1", 0)

    @pytest.mark.asyncio
    async def test_declined_resumes_graph_without_ingest(self):
        """Declined resume skips ingest and resumes graph."""
        repo = AsyncMock()
        pending_turn = MagicMock()
        pending_turn.turn_number = 0
        pending_turn.pending_confirmation = {"papers": [], "proposed_ids": []}
        repo.get_pending_turn = AsyncMock(return_value=pending_turn)
        repo.get_turn_count = AsyncMock(return_value=1)
        saved_turn = MagicMock()
        saved_turn.turn_number = 1
        repo.save_turn = AsyncMock(return_value=saved_turn)
        repo.clear_pending_confirmation = AsyncMock()

        service = _make_service(
            graph_events=[
                ("updates", {"generate": {"messages": []}}),
            ],
            conversation_repo=repo,
        )

        events = []
        async for event in service.resume_stream(
            session_id="s1",
            thread_id="s1:0",
            approved=False,
            selected_ids=[],
        ):
            events.append(event)

        event_types = [e.event for e in events]
        # Should NOT have ingest events
        assert StreamEventType.INGEST_COMPLETE not in event_types
        assert StreamEventType.METADATA in event_types
        assert StreamEventType.DONE in event_types

        # Verify synthetic query for decline
        turn_data = repo.save_turn.call_args[0][1]
        assert "Declined" in turn_data.user_query

    @pytest.mark.asyncio
    async def test_checkpoint_expired_clears_pending(self):
        """When graph raises checkpoint error, emit ERROR(CHECKPOINT_EXPIRED)."""
        repo = AsyncMock()
        pending_turn = MagicMock()
        pending_turn.turn_number = 0
        pending_turn.pending_confirmation = {"papers": [], "proposed_ids": []}
        repo.get_pending_turn = AsyncMock(return_value=pending_turn)
        repo.clear_pending_confirmation = AsyncMock()

        # Make graph raise a checkpoint error
        llm_client = _make_llm_client()
        search_service = MagicMock()
        graph = AsyncMock()

        async def failing_astream(input_data, config, stream_mode=None):
            raise RuntimeError("No checkpoint found for thread s1:0")
            yield  # make it a generator

        graph.astream = failing_astream

        service = AgentService(
            llm_client=llm_client,
            search_service=search_service,
            graph=graph,
            redis=AsyncMock(),
            conversation_repo=repo,
            **_make_context_kwargs(),
        )

        events = []
        async for event in service.resume_stream(
            session_id="s1",
            thread_id="s1:0",
            approved=True,
            selected_ids=["2301.00001"],
        ):
            events.append(event)

        event_types = [e.event for e in events]
        assert StreamEventType.ERROR in event_types
        assert StreamEventType.DONE in event_types

        error_event = next(e for e in events if e.event == StreamEventType.ERROR)
        assert error_event.data.code == "CHECKPOINT_EXPIRED"

        # Verify pending was cleared
        repo.clear_pending_confirmation.assert_called_once_with("s1", 0)
