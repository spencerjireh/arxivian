"""Tests for AgentExecutionRepository."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock

from src.repositories.agent_execution_repository import AgentExecutionRepository


class TestAgentExecutionRepositorySaveState:
    """Tests for AgentExecutionRepository.save_state method."""

    @pytest.fixture
    def execution_repository(self, mock_async_session):
        return AgentExecutionRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_save_state_creates_execution(
        self, execution_repository, mock_async_session
    ):
        """Verify execution is created."""
        state = {"messages": [], "iteration": 0}

        await execution_repository.save_state(
            session_id="test-session",
            state_snapshot=state,
            status="running",
            iteration=0,
        )

        mock_async_session.add.assert_called_once()
        mock_async_session.commit.assert_called_once()
        mock_async_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_state_stores_snapshot(
        self, execution_repository, mock_async_session
    ):
        """Verify state_snapshot is stored."""
        state = {"messages": [{"role": "user", "content": "test"}], "iteration": 1}

        await execution_repository.save_state(
            session_id="test-session",
            state_snapshot=state,
        )

        # Verify add was called with an execution
        mock_async_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_state_sets_status(
        self, execution_repository, mock_async_session
    ):
        """Verify status field is set."""
        await execution_repository.save_state(
            session_id="test-session",
            state_snapshot={},
            status="paused",
        )

        mock_async_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_state_with_pause_reason(
        self, execution_repository, mock_async_session
    ):
        """Verify pause_reason is stored."""
        await execution_repository.save_state(
            session_id="test-session",
            state_snapshot={},
            status="paused",
            pause_reason="Waiting for user input",
        )

        mock_async_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_state_with_error_message(
        self, execution_repository, mock_async_session
    ):
        """Verify error_message is stored."""
        await execution_repository.save_state(
            session_id="test-session",
            state_snapshot={},
            status="failed",
            error_message="LLM timeout",
        )

        mock_async_session.add.assert_called_once()


class TestAgentExecutionRepositoryLoadState:
    """Tests for AgentExecutionRepository.load_state method."""

    @pytest.fixture
    def execution_repository(self, mock_async_session):
        return AgentExecutionRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_load_state_returns_execution(
        self, execution_repository, mock_async_session, mock_agent_execution
    ):
        """Verify retrieval by ID."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_agent_execution
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.load_state(mock_agent_execution.id)

        assert result is mock_agent_execution

    @pytest.mark.asyncio
    async def test_load_state_returns_none(
        self, execution_repository, mock_async_session
    ):
        """Verify None for non-existent ID."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.load_state(uuid.uuid4())

        assert result is None


class TestAgentExecutionRepositoryLoadLatestPaused:
    """Tests for AgentExecutionRepository.load_latest_paused method."""

    @pytest.fixture
    def execution_repository(self, mock_async_session):
        return AgentExecutionRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_load_latest_paused_filters_status(
        self, execution_repository, mock_async_session, mock_agent_execution
    ):
        """Verify status='paused' filter."""
        mock_agent_execution.status = "paused"
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_agent_execution
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.load_latest_paused("test-session")

        assert result is mock_agent_execution

    @pytest.mark.asyncio
    async def test_load_latest_paused_returns_none(
        self, execution_repository, mock_async_session
    ):
        """Verify None when no paused execution."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.load_latest_paused("test-session")

        assert result is None


class TestAgentExecutionRepositoryUpdateStatus:
    """Tests for AgentExecutionRepository.update_status method."""

    @pytest.fixture
    def execution_repository(self, mock_async_session):
        return AgentExecutionRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_update_status_modifies_execution(
        self, execution_repository, mock_async_session, mock_agent_execution
    ):
        """Verify fields are updated."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_agent_execution
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.update_status(
            execution_id=mock_agent_execution.id,
            status="completed",
        )

        assert mock_agent_execution.status == "completed"
        mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_returns_none_for_missing(
        self, execution_repository, mock_async_session
    ):
        """Verify None for non-existent execution."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.update_status(
            execution_id=uuid.uuid4(),
            status="completed",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_status_with_state_snapshot(
        self, execution_repository, mock_async_session, mock_agent_execution
    ):
        """Verify state_snapshot can be updated."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_agent_execution
        mock_async_session.execute.return_value = mock_result

        new_state = {"messages": [], "iteration": 5}
        await execution_repository.update_status(
            execution_id=mock_agent_execution.id,
            status="completed",
            state_snapshot=new_state,
        )

        assert mock_agent_execution.state_snapshot == new_state


class TestAgentExecutionRepositoryGetBySession:
    """Tests for AgentExecutionRepository.get_by_session method."""

    @pytest.fixture
    def execution_repository(self, mock_async_session):
        return AgentExecutionRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_get_by_session_returns_list(
        self, execution_repository, mock_async_session, mock_agent_execution
    ):
        """Verify session filtering."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_agent_execution]
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.get_by_session("test-session")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_session_respects_limit(
        self, execution_repository, mock_async_session
    ):
        """Verify limit parameter."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_session.execute.return_value = mock_result

        await execution_repository.get_by_session("test-session", limit=5)

        mock_async_session.execute.assert_called_once()


class TestAgentExecutionRepositoryDelete:
    """Tests for AgentExecutionRepository.delete method."""

    @pytest.fixture
    def execution_repository(self, mock_async_session):
        return AgentExecutionRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_delete_removes_execution(
        self, execution_repository, mock_async_session, mock_agent_execution
    ):
        """Verify deletion."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_agent_execution
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.delete(mock_agent_execution.id)

        assert result is True
        mock_async_session.delete.assert_called_once()
        mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_deleted(
        self, execution_repository, mock_async_session, mock_agent_execution
    ):
        """Verify True when deleted."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_agent_execution
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.delete(mock_agent_execution.id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self, execution_repository, mock_async_session
    ):
        """Verify False when not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.delete(uuid.uuid4())

        assert result is False


class TestAgentExecutionRepositoryCleanup:
    """Tests for AgentExecutionRepository.cleanup_old_executions method."""

    @pytest.fixture
    def execution_repository(self, mock_async_session):
        return AgentExecutionRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_cleanup_old_executions_keeps_recent(
        self, execution_repository, mock_async_session, mock_agent_execution
    ):
        """Verify keep_count is respected."""
        # Create 7 executions
        executions = [Mock() for _ in range(7)]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = executions
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.cleanup_old_executions(
            "test-session", keep_count=5
        )

        # Should delete 2 (7 - 5)
        assert result == 2
        assert mock_async_session.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_old_executions_returns_count(
        self, execution_repository, mock_async_session
    ):
        """Verify deleted count is returned."""
        executions = [Mock() for _ in range(3)]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = executions
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.cleanup_old_executions(
            "test-session", keep_count=1
        )

        assert result == 2

    @pytest.mark.asyncio
    async def test_cleanup_old_executions_no_deletions(
        self, execution_repository, mock_async_session
    ):
        """Verify no deletion when within limit."""
        executions = [Mock() for _ in range(3)]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = executions
        mock_async_session.execute.return_value = mock_result

        result = await execution_repository.cleanup_old_executions(
            "test-session", keep_count=5
        )

        assert result == 0
        mock_async_session.delete.assert_not_called()
