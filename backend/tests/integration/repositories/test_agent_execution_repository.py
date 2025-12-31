"""Integration tests for AgentExecutionRepository."""

import pytest
import uuid

from src.repositories.agent_execution_repository import AgentExecutionRepository


class TestAgentExecutionRepositorySaveLoad:
    """Test save and load state operations."""

    @pytest.mark.asyncio
    async def test_save_state_creates_execution(self, db_session):
        """Verify save_state creates a new execution record."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"
        state_snapshot = {"messages": [], "iteration": 0}

        execution = await repo.save_state(
            session_id=session_id,
            state_snapshot=state_snapshot,
            status="running",
            iteration=0,
        )

        assert execution.id is not None
        assert execution.session_id == session_id
        assert execution.state_snapshot == state_snapshot
        assert execution.status == "running"
        assert execution.iteration == 0

    @pytest.mark.asyncio
    async def test_save_state_with_pause_reason(self, db_session):
        """Verify save_state stores pause reason."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        execution = await repo.save_state(
            session_id=session_id,
            state_snapshot={"messages": []},
            status="paused",
            iteration=1,
            pause_reason="Waiting for user input",
        )

        assert execution.status == "paused"
        assert execution.pause_reason == "Waiting for user input"

    @pytest.mark.asyncio
    async def test_save_state_with_error_message(self, db_session):
        """Verify save_state stores error message."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        execution = await repo.save_state(
            session_id=session_id,
            state_snapshot={"messages": []},
            status="failed",
            iteration=2,
            error_message="Something went wrong",
        )

        assert execution.status == "failed"
        assert execution.error_message == "Something went wrong"

    @pytest.mark.asyncio
    async def test_load_state(self, db_session):
        """Verify load_state retrieves execution by ID."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"
        state_snapshot = {"messages": ["test"], "iteration": 5}

        execution = await repo.save_state(
            session_id=session_id,
            state_snapshot=state_snapshot,
            status="running",
            iteration=5,
        )

        loaded = await repo.load_state(str(execution.id))

        assert loaded is not None
        assert loaded.id == execution.id
        assert loaded.state_snapshot == state_snapshot

    @pytest.mark.asyncio
    async def test_load_state_not_found(self, db_session):
        """Verify load_state returns None for nonexistent ID."""
        repo = AgentExecutionRepository(session=db_session)

        loaded = await repo.load_state(str(uuid.uuid4()))
        assert loaded is None


class TestAgentExecutionRepositoryPaused:
    """Test paused execution operations."""

    @pytest.mark.asyncio
    async def test_load_latest_paused(self, db_session):
        """Verify load_latest_paused returns most recent paused execution."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        # Create running execution
        await repo.save_state(
            session_id=session_id,
            state_snapshot={"iteration": 1},
            status="running",
            iteration=1,
        )

        # Create paused execution
        paused = await repo.save_state(
            session_id=session_id,
            state_snapshot={"iteration": 2},
            status="paused",
            iteration=2,
            pause_reason="User pause",
        )

        loaded = await repo.load_latest_paused(session_id)

        assert loaded is not None
        assert loaded.id == paused.id
        assert loaded.status == "paused"

    @pytest.mark.asyncio
    async def test_load_latest_paused_no_paused_execution(self, db_session):
        """Verify load_latest_paused returns None when no paused executions."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        await repo.save_state(
            session_id=session_id,
            state_snapshot={},
            status="running",
            iteration=0,
        )

        loaded = await repo.load_latest_paused(session_id)
        assert loaded is None


class TestAgentExecutionRepositoryUpdate:
    """Test update operations."""

    @pytest.mark.asyncio
    async def test_update_status(self, db_session):
        """Verify update_status modifies execution."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        execution = await repo.save_state(
            session_id=session_id,
            state_snapshot={"iteration": 0},
            status="running",
            iteration=0,
        )

        updated = await repo.update_status(
            str(execution.id),
            status="completed",
        )

        assert updated is not None
        assert updated.status == "completed"

    @pytest.mark.asyncio
    async def test_update_status_with_state_snapshot(self, db_session):
        """Verify update_status can update state snapshot."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        execution = await repo.save_state(
            session_id=session_id,
            state_snapshot={"iteration": 0},
            status="running",
            iteration=0,
        )

        new_snapshot = {"iteration": 5, "messages": ["updated"]}
        updated = await repo.update_status(
            str(execution.id),
            status="paused",
            state_snapshot=new_snapshot,
            pause_reason="Checkpoint",
        )

        assert updated is not None
        assert updated.state_snapshot == new_snapshot
        assert updated.pause_reason == "Checkpoint"

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, db_session):
        """Verify update_status returns None for nonexistent ID."""
        repo = AgentExecutionRepository(session=db_session)

        updated = await repo.update_status(str(uuid.uuid4()), status="completed")
        assert updated is None


class TestAgentExecutionRepositoryQuery:
    """Test query operations."""

    @pytest.mark.asyncio
    async def test_get_by_session(self, db_session):
        """Verify get_by_session returns executions for session."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        for i in range(3):
            await repo.save_state(
                session_id=session_id,
                state_snapshot={"iteration": i},
                status="completed",
                iteration=i,
            )

        executions = await repo.get_by_session(session_id)

        assert len(executions) == 3

    @pytest.mark.asyncio
    async def test_get_by_session_respects_limit(self, db_session):
        """Verify get_by_session respects limit parameter."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        for i in range(5):
            await repo.save_state(
                session_id=session_id,
                state_snapshot={"iteration": i},
                status="completed",
                iteration=i,
            )

        executions = await repo.get_by_session(session_id, limit=2)

        assert len(executions) == 2


class TestAgentExecutionRepositoryDelete:
    """Test delete operations."""

    @pytest.mark.asyncio
    async def test_delete(self, db_session):
        """Verify delete removes execution."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        execution = await repo.save_state(
            session_id=session_id,
            state_snapshot={},
            status="running",
            iteration=0,
        )

        deleted = await repo.delete(str(execution.id))
        assert deleted is True

        loaded = await repo.load_state(str(execution.id))
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, db_session):
        """Verify delete returns False for nonexistent ID."""
        repo = AgentExecutionRepository(session=db_session)

        deleted = await repo.delete(str(uuid.uuid4()))
        assert deleted is False

    @pytest.mark.asyncio
    async def test_cleanup_old_executions(self, db_session):
        """Verify cleanup_old_executions keeps only recent executions."""
        repo = AgentExecutionRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        # Create 5 executions
        for i in range(5):
            await repo.save_state(
                session_id=session_id,
                state_snapshot={"iteration": i},
                status="completed",
                iteration=i,
            )

        # Keep only 2 most recent
        deleted_count = await repo.cleanup_old_executions(session_id, keep_count=2)

        assert deleted_count == 3

        remaining = await repo.get_by_session(session_id)
        assert len(remaining) == 2
