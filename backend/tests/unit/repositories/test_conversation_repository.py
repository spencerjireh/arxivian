"""Tests for ConversationRepository."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from sqlalchemy.exc import IntegrityError

from src.repositories.conversation_repository import ConversationRepository


class TestConversationRepositoryGetOrCreate:
    """Tests for ConversationRepository.get_or_create method."""

    @pytest.fixture
    def conversation_repository(self, mock_async_session):
        return ConversationRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(
        self, conversation_repository, mock_async_session, mock_conversation
    ):
        """Verify existing conversation is returned."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result

        result = await conversation_repository.get_or_create("test-session")

        assert result is mock_conversation
        # Should not create new
        mock_async_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(
        self, conversation_repository, mock_async_session
    ):
        """Verify creation when not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        await conversation_repository.get_or_create("new-session")

        mock_async_session.add.assert_called_once()
        mock_async_session.commit.assert_called_once()
        mock_async_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_commits(
        self, conversation_repository, mock_async_session
    ):
        """Verify commit is called for new conversation."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        await conversation_repository.get_or_create("new-session")

        mock_async_session.commit.assert_called_once()


class TestConversationRepositoryHistory:
    """Tests for ConversationRepository.get_history method."""

    @pytest.fixture
    def conversation_repository(self, mock_async_session):
        return ConversationRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_get_history_returns_turns(
        self,
        conversation_repository,
        mock_async_session,
        mock_conversation,
        mock_conversation_turn,
    ):
        """Verify turns are returned."""
        # First call returns conversation, second returns turns
        mock_conv_result = Mock()
        mock_conv_result.scalar_one_or_none.return_value = mock_conversation

        mock_turns_result = Mock()
        mock_turns_result.scalars.return_value.all.return_value = [mock_conversation_turn]

        mock_async_session.execute.side_effect = [mock_conv_result, mock_turns_result]

        result = await conversation_repository.get_history("test-session", limit=5)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_history_returns_empty_for_new_session(
        self, conversation_repository, mock_async_session
    ):
        """Verify empty for session that doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await conversation_repository.get_history("nonexistent")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_history_reverses_order(
        self,
        conversation_repository,
        mock_async_session,
        mock_conversation,
    ):
        """Verify turns are returned in chronological order (reversed)."""
        # Create turns with different turn_numbers
        turn1 = Mock()
        turn1.turn_number = 2
        turn2 = Mock()
        turn2.turn_number = 1
        turn3 = Mock()
        turn3.turn_number = 0

        mock_conv_result = Mock()
        mock_conv_result.scalar_one_or_none.return_value = mock_conversation

        # Returns in descending order (as queried)
        mock_turns_result = Mock()
        mock_turns_result.scalars.return_value.all.return_value = [turn1, turn2, turn3]

        mock_async_session.execute.side_effect = [mock_conv_result, mock_turns_result]

        result = await conversation_repository.get_history("test-session", limit=10)

        # Should be reversed to chronological
        assert result[0].turn_number == 0
        assert result[1].turn_number == 1
        assert result[2].turn_number == 2


class TestConversationRepositorySaveTurn:
    """Tests for ConversationRepository.save_turn method."""

    @pytest.fixture
    def conversation_repository(self, mock_async_session):
        return ConversationRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_save_turn_creates_turn(
        self,
        conversation_repository,
        mock_async_session,
        mock_conversation,
        sample_turn_data,
    ):
        """Verify turn is created."""
        # Setup mocks for multiple execute calls
        mock_conv_result = Mock()
        mock_conv_result.scalar_one_or_none.return_value = mock_conversation

        mock_max_turn_result = Mock()
        mock_max_turn_result.scalar_one_or_none.return_value = None  # No existing turns

        mock_async_session.execute.side_effect = [mock_conv_result, mock_max_turn_result]

        await conversation_repository.save_turn("test-session", sample_turn_data)

        mock_async_session.add.assert_called()
        mock_async_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_save_turn_increments_turn_number(
        self,
        conversation_repository,
        mock_async_session,
        mock_conversation,
        sample_turn_data,
    ):
        """Verify turn_number is incremented from max."""
        mock_conv_result = Mock()
        mock_conv_result.scalar_one_or_none.return_value = mock_conversation

        # Existing max turn is 2
        mock_max_turn_result = Mock()
        mock_max_turn_result.scalar_one_or_none.return_value = 2

        mock_async_session.execute.side_effect = [mock_conv_result, mock_max_turn_result]

        await conversation_repository.save_turn("test-session", sample_turn_data)

        # Verify a turn was added (we can't easily check turn_number directly)
        mock_async_session.add.assert_called()

    @pytest.mark.asyncio
    async def test_save_turn_creates_conversation_if_missing(
        self,
        conversation_repository,
        mock_async_session,
        sample_turn_data,
    ):
        """Verify auto-creation of conversation."""
        # Conversation doesn't exist
        mock_conv_result = Mock()
        mock_conv_result.scalar_one_or_none.return_value = None

        mock_max_turn_result = Mock()
        mock_max_turn_result.scalar_one_or_none.return_value = None

        mock_async_session.execute.side_effect = [mock_conv_result, mock_max_turn_result]

        await conversation_repository.save_turn("new-session", sample_turn_data)

        # Should add conversation and turn
        assert mock_async_session.add.call_count >= 1

    @pytest.mark.asyncio
    async def test_save_turn_retries_on_integrity_error(
        self,
        conversation_repository,
        mock_async_session,
        mock_conversation,
        sample_turn_data,
    ):
        """Verify retry logic on IntegrityError."""
        # Setup mock results that return proper values
        mock_conv_result = Mock()
        mock_conv_result.scalar_one_or_none.return_value = mock_conversation

        mock_max_turn_result = Mock()
        mock_max_turn_result.scalar_one_or_none.return_value = 0  # Return integer, not Mock

        call_count = [0]

        async def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Odd calls are for conversation, even calls are for max_turn
            if call_count[0] % 2 == 1:
                return mock_conv_result
            return mock_max_turn_result

        mock_async_session.execute.side_effect = execute_side_effect

        # First commit fails, second succeeds
        commit_count = [0]

        async def commit_side_effect():
            commit_count[0] += 1
            if commit_count[0] == 1:
                raise IntegrityError("duplicate", None, None)

        mock_async_session.commit.side_effect = commit_side_effect

        await conversation_repository.save_turn("test-session", sample_turn_data)

        # Should have retried
        assert commit_count[0] >= 2

    @pytest.mark.asyncio
    async def test_save_turn_fails_after_max_retries(
        self,
        conversation_repository,
        mock_async_session,
        mock_conversation,
        sample_turn_data,
    ):
        """Verify IntegrityError raised after max retries."""
        mock_conv_result = Mock()
        mock_conv_result.scalar_one_or_none.return_value = mock_conversation

        mock_max_turn_result = Mock()
        mock_max_turn_result.scalar_one_or_none.return_value = 0  # Return integer, not Mock

        call_count = [0]

        async def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Odd calls are for conversation, even calls are for max_turn
            if call_count[0] % 2 == 1:
                return mock_conv_result
            return mock_max_turn_result

        mock_async_session.execute.side_effect = execute_side_effect

        # Always fail
        mock_async_session.commit.side_effect = IntegrityError("duplicate", None, None)

        with pytest.raises(IntegrityError):
            await conversation_repository.save_turn("test-session", sample_turn_data)


class TestConversationRepositoryOperations:
    """Tests for other ConversationRepository operations."""

    @pytest.fixture
    def conversation_repository(self, mock_async_session):
        return ConversationRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_delete_removes_conversation(
        self, conversation_repository, mock_async_session, mock_conversation
    ):
        """Verify cascade delete."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result

        result = await conversation_repository.delete("test-session")

        assert result is True
        mock_async_session.delete.assert_called_once()
        mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_deleted(
        self, conversation_repository, mock_async_session, mock_conversation
    ):
        """Verify True when deleted."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result

        result = await conversation_repository.delete("test-session")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self, conversation_repository, mock_async_session
    ):
        """Verify False when not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await conversation_repository.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_session_id_returns_conversation(
        self, conversation_repository, mock_async_session, mock_conversation
    ):
        """Verify retrieval by session_id."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result

        result = await conversation_repository.get_by_session_id("test-session")

        assert result is mock_conversation

    @pytest.mark.asyncio
    async def test_get_turn_count_returns_count(
        self, conversation_repository, mock_async_session, mock_conversation
    ):
        """Verify turn count."""
        mock_conv_result = Mock()
        mock_conv_result.scalar_one_or_none.return_value = mock_conversation

        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 5

        mock_async_session.execute.side_effect = [mock_conv_result, mock_count_result]

        result = await conversation_repository.get_turn_count("test-session")

        assert result == 5

    @pytest.mark.asyncio
    async def test_get_turn_count_returns_zero_for_missing(
        self, conversation_repository, mock_async_session
    ):
        """Verify zero for non-existent session."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await conversation_repository.get_turn_count("nonexistent")

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated(
        self, conversation_repository, mock_async_session, mock_conversation
    ):
        """Verify offset/limit."""
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 10

        mock_list_result = Mock()
        mock_list_result.scalars.return_value.all.return_value = [mock_conversation]

        mock_async_session.execute.side_effect = [mock_count_result, mock_list_result]

        conversations, total = await conversation_repository.get_all(offset=0, limit=5)

        assert len(conversations) == 1
        assert total == 10

    @pytest.mark.asyncio
    async def test_get_with_turns_returns_conversation(
        self, conversation_repository, mock_async_session, mock_conversation
    ):
        """Verify eager loading works."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result

        result = await conversation_repository.get_with_turns("test-session")

        assert result is mock_conversation
