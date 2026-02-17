"""Integration tests for ConversationRepository."""

import pytest
import uuid

from src.models.user import User
from src.repositories.conversation_repository import ConversationRepository
from src.schemas.conversation import TurnData


# =============================================================================
# User Fixtures for Ownership Tests
# =============================================================================


@pytest.fixture
async def test_user_1(db_session) -> User:
    """Create first test user for ownership tests."""
    user = User(
        clerk_id=f"test_user_1_{uuid.uuid4().hex[:8]}",
        email=f"user1-{uuid.uuid4().hex[:8]}@test.com",
        first_name="Test",
        last_name="User1",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def test_user_2(db_session) -> User:
    """Create second test user for ownership tests."""
    user = User(
        clerk_id=f"test_user_2_{uuid.uuid4().hex[:8]}",
        email=f"user2-{uuid.uuid4().hex[:8]}@test.com",
        first_name="Test",
        last_name="User2",
    )
    db_session.add(user)
    await db_session.flush()
    return user


class TestConversationRepositoryCRUD:
    """Test conversation CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(self, db_session):
        """Verify new conversation is created if not exists."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"
        conv = await repo.get_or_create(session_id)

        assert conv.id is not None
        assert conv.session_id == session_id

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(self, db_session):
        """Verify existing conversation is returned."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"
        conv1 = await repo.get_or_create(session_id)
        conv2 = await repo.get_or_create(session_id)

        assert conv1.id == conv2.id

    @pytest.mark.asyncio
    async def test_get_by_session_id(self, db_session):
        """Verify retrieving conversation by session ID."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"
        created = await repo.get_or_create(session_id)

        retrieved = await repo.get_by_session_id(session_id)

        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_session_id_not_found(self, db_session):
        """Verify None returned for nonexistent session."""
        repo = ConversationRepository(session=db_session)

        retrieved = await repo.get_by_session_id("nonexistent-session")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_conversation(self, db_session):
        """Verify conversation can be deleted."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"
        await repo.get_or_create(session_id)

        deleted = await repo.delete(session_id)
        assert deleted is True

        retrieved = await repo.get_by_session_id(session_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(self, db_session):
        """Verify deleting nonexistent conversation returns False."""
        repo = ConversationRepository(session=db_session)

        deleted = await repo.delete("nonexistent-session")
        assert deleted is False


class TestConversationRepositoryTurns:
    """Test conversation turn operations."""

    @pytest.mark.asyncio
    async def test_save_turn(self, db_session):
        """Verify turn can be saved."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"
        turn = TurnData(
            user_query="What is ML?",
            agent_response="Machine learning is...",
            provider="openai",
            model="gpt-4o-mini",
            guardrail_score=90,
        )

        saved_turn = await repo.save_turn(session_id, turn)

        assert saved_turn.id is not None
        assert saved_turn.user_query == "What is ML?"
        assert saved_turn.turn_number == 0

    @pytest.mark.asyncio
    async def test_save_multiple_turns_increments_number(self, db_session):
        """Verify turn numbers increment correctly."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        for i in range(3):
            turn = TurnData(
                user_query=f"Question {i}",
                agent_response=f"Answer {i}",
                provider="openai",
                model="gpt-4o-mini",
            )
            saved = await repo.save_turn(session_id, turn)
            assert saved.turn_number == i

    @pytest.mark.asyncio
    async def test_get_history(self, db_session):
        """Verify conversation history retrieval."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        for i in range(3):
            turn = TurnData(
                user_query=f"Question {i}",
                agent_response=f"Answer {i}",
                provider="openai",
                model="gpt-4o-mini",
            )
            await repo.save_turn(session_id, turn)

        history = await repo.get_history(session_id, limit=10)

        assert len(history) == 3
        # Verify chronological order
        assert history[0].user_query == "Question 0"
        assert history[1].user_query == "Question 1"
        assert history[2].user_query == "Question 2"

    @pytest.mark.asyncio
    async def test_get_history_respects_limit(self, db_session):
        """Verify history limit is respected."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        for i in range(5):
            turn = TurnData(
                user_query=f"Question {i}",
                agent_response=f"Answer {i}",
                provider="openai",
                model="gpt-4o-mini",
            )
            await repo.save_turn(session_id, turn)

        history = await repo.get_history(session_id, limit=2)

        # Should return most recent 2 turns in chronological order
        assert len(history) == 2
        assert history[0].user_query == "Question 3"
        assert history[1].user_query == "Question 4"

    @pytest.mark.asyncio
    async def test_get_turn_count(self, db_session):
        """Verify turn count is correct."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        for i in range(4):
            turn = TurnData(
                user_query=f"Question {i}",
                agent_response=f"Answer {i}",
                provider="openai",
                model="gpt-4o-mini",
            )
            await repo.save_turn(session_id, turn)

        count = await repo.get_turn_count(session_id)
        assert count == 4

    @pytest.mark.asyncio
    async def test_get_turn_count_nonexistent_session(self, db_session):
        """Verify turn count is 0 for nonexistent session."""
        repo = ConversationRepository(session=db_session)

        count = await repo.get_turn_count("nonexistent-session")
        assert count == 0


class TestConversationRepositoryThinkingSteps:
    """Test thinking_steps persistence."""

    @pytest.mark.asyncio
    async def test_save_turn_with_thinking_steps(self, db_session):
        """Verify thinking_steps roundtrip through save and retrieval."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"
        steps = [
            {
                "step": "guardrail",
                "message": "Query is in scope",
                "details": {"score": 85, "threshold": 50},
                "tool_name": None,
                "started_at": "2026-02-15T10:00:00+00:00",
                "completed_at": "2026-02-15T10:00:01+00:00",
            },
            {
                "step": "executing",
                "message": "retrieve completed",
                "details": {"tool_name": "retrieve", "success": True},
                "tool_name": "retrieve",
                "started_at": "2026-02-15T10:00:02+00:00",
                "completed_at": "2026-02-15T10:00:03+00:00",
            },
        ]
        turn = TurnData(
            user_query="What is ML?",
            agent_response="Machine learning is...",
            provider="openai",
            model="gpt-4o-mini",
            thinking_steps=steps,
        )

        saved = await repo.save_turn(session_id, turn)

        assert saved.thinking_steps is not None
        assert len(saved.thinking_steps) == 2
        assert saved.thinking_steps[0]["step"] == "guardrail"
        assert saved.thinking_steps[0]["details"]["score"] == 85
        assert saved.thinking_steps[1]["tool_name"] == "retrieve"

    @pytest.mark.asyncio
    async def test_save_turn_without_thinking_steps(self, db_session):
        """Verify None default for backward compat."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"
        turn = TurnData(
            user_query="What is ML?",
            agent_response="Machine learning is...",
            provider="openai",
            model="gpt-4o-mini",
        )

        saved = await repo.save_turn(session_id, turn)

        assert saved.thinking_steps is None


class TestConversationRepositoryPagination:
    """Test conversation list pagination."""

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, db_session):
        """Verify pagination for conversation list."""
        repo = ConversationRepository(session=db_session)

        # Create multiple conversations
        for i in range(5):
            session_id = f"session-page-{uuid.uuid4().hex[:8]}-{i}"
            turn = TurnData(
                user_query=f"Query {i}",
                agent_response=f"Response {i}",
                provider="openai",
                model="gpt-4o-mini",
            )
            await repo.save_turn(session_id, turn)

        conversations, total = await repo.get_all(offset=0, limit=2)

        assert total >= 5
        assert len(conversations) == 2

    @pytest.mark.asyncio
    async def test_get_with_turns(self, db_session):
        """Verify eager loading of turns."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        for i in range(2):
            turn = TurnData(
                user_query=f"Query {i}",
                agent_response=f"Response {i}",
                provider="openai",
                model="gpt-4o-mini",
            )
            await repo.save_turn(session_id, turn)

        conv = await repo.get_with_turns(session_id)

        assert conv is not None
        assert len(conv.turns) == 2


class TestConversationRepositoryCascadeDelete:
    """Test cascade delete of turns with conversation."""

    @pytest.mark.asyncio
    async def test_delete_cascades_to_turns(self, db_session):
        """Verify turns are deleted when conversation is deleted."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        for i in range(3):
            turn = TurnData(
                user_query=f"Query {i}",
                agent_response=f"Response {i}",
                provider="openai",
                model="gpt-4o-mini",
            )
            await repo.save_turn(session_id, turn)

        assert await repo.get_turn_count(session_id) == 3

        await repo.delete(session_id)

        assert await repo.get_turn_count(session_id) == 0


class TestConversationRepositoryUserFiltering:
    """Test user_id filtering for conversation ownership."""

    @pytest.mark.asyncio
    async def test_get_or_create_with_user_id(self, db_session, test_user_1):
        """Verify user_id is set on new conversation."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        conv = await repo.get_or_create(session_id, user_id=test_user_1.id)

        assert conv.user_id == test_user_1.id

    @pytest.mark.asyncio
    async def test_save_turn_with_user_id(self, db_session, test_user_1):
        """Verify user_id is set when saving turn creates new conversation."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        turn = TurnData(
            user_query="Question",
            agent_response="Answer",
            provider="openai",
            model="gpt-4o-mini",
        )
        await repo.save_turn(session_id, turn, user_id=test_user_1.id)

        conv = await repo.get_by_session_id(session_id)
        assert conv is not None
        assert conv.user_id == test_user_1.id

    @pytest.mark.asyncio
    async def test_get_all_filters_by_user_id(self, db_session, test_user_1, test_user_2):
        """Verify get_all filters by user_id."""
        repo = ConversationRepository(session=db_session)

        # Create conversations for user 1
        for i in range(2):
            session_id = f"session-user1-{uuid.uuid4().hex[:8]}"
            turn = TurnData(
                user_query=f"Query {i}",
                agent_response=f"Response {i}",
                provider="openai",
                model="gpt-4o-mini",
            )
            await repo.save_turn(session_id, turn, user_id=test_user_1.id)

        # Create conversations for user 2
        for i in range(3):
            session_id = f"session-user2-{uuid.uuid4().hex[:8]}"
            turn = TurnData(
                user_query=f"Query {i}",
                agent_response=f"Response {i}",
                provider="openai",
                model="gpt-4o-mini",
            )
            await repo.save_turn(session_id, turn, user_id=test_user_2.id)

        # Get all for user 1
        convs_1, total_1 = await repo.get_all(user_id=test_user_1.id)
        assert total_1 == 2
        assert len(convs_1) == 2

        # Get all for user 2
        convs_2, total_2 = await repo.get_all(user_id=test_user_2.id)
        assert total_2 == 3
        assert len(convs_2) == 3

    @pytest.mark.asyncio
    async def test_get_by_session_id_with_user_id_filter(
        self, db_session, test_user_1, test_user_2
    ):
        """Verify get_by_session_id filters by user_id."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        await repo.get_or_create(session_id, user_id=test_user_1.id)

        # Owner can access
        conv = await repo.get_by_session_id(session_id, user_id=test_user_1.id)
        assert conv is not None

        # Other user cannot access
        conv = await repo.get_by_session_id(session_id, user_id=test_user_2.id)
        assert conv is None

    @pytest.mark.asyncio
    async def test_get_with_turns_filters_by_user_id(self, db_session, test_user_1, test_user_2):
        """Verify get_with_turns filters by user_id."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        turn = TurnData(
            user_query="Question",
            agent_response="Answer",
            provider="openai",
            model="gpt-4o-mini",
        )
        await repo.save_turn(session_id, turn, user_id=test_user_1.id)

        # Owner can access with turns
        conv = await repo.get_with_turns(session_id, user_id=test_user_1.id)
        assert conv is not None
        assert len(conv.turns) == 1

        # Other user cannot access
        conv = await repo.get_with_turns(session_id, user_id=test_user_2.id)
        assert conv is None

    @pytest.mark.asyncio
    async def test_delete_filters_by_user_id(self, db_session, test_user_1, test_user_2):
        """Verify delete filters by user_id."""
        repo = ConversationRepository(session=db_session)

        session_id = f"session-{uuid.uuid4().hex[:8]}"

        await repo.get_or_create(session_id, user_id=test_user_1.id)

        # Other user cannot delete
        deleted = await repo.delete(session_id, user_id=test_user_2.id)
        assert deleted is False

        # Conversation still exists
        conv = await repo.get_by_session_id(session_id)
        assert conv is not None

        # Owner can delete
        deleted = await repo.delete(session_id, user_id=test_user_1.id)
        assert deleted is True

        # Conversation is gone
        conv = await repo.get_by_session_id(session_id)
        assert conv is None
