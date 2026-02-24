"""Repository for Conversation model operations."""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from src.models.conversation import Conversation, ConversationTurn
from src.schemas.conversation import TurnData
from src.utils.logger import get_logger

log = get_logger(__name__)


class ConversationRepository:
    """Repository for conversation CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def commit(self) -> None:
        """Flush and commit the current transaction."""
        await self.session.commit()

    async def get_or_create(self, session_id: str, user_id: Optional[UUID] = None) -> Conversation:
        """
        Get existing conversation or create new one.

        Args:
            session_id: Unique session identifier
            user_id: Optional user ID to associate with the conversation

        Returns:
            Conversation instance
        """
        query = select(Conversation).where(Conversation.session_id == session_id)
        if user_id is not None:
            query = query.where(Conversation.user_id == user_id)

        result = await self.session.execute(query)
        conv = result.scalar_one_or_none()

        if not conv:
            conv = Conversation(session_id=session_id, user_id=user_id)
            self.session.add(conv)
            await self.session.flush()
            await self.session.refresh(conv)
            log.debug("conversation created", session_id=session_id, user_id=str(user_id))
        else:
            log.debug("conversation found", session_id=session_id)

        return conv

    async def get_history(
        self, session_id: str, limit: int = 5, user_id: Optional[UUID] = None
    ) -> List[ConversationTurn]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of turns to return
            user_id: Optional user ID for ownership verification

        Returns:
            List of ConversationTurn in chronological order
        """
        query = select(Conversation).where(Conversation.session_id == session_id)
        if user_id is not None:
            query = query.where(Conversation.user_id == user_id)

        result = await self.session.execute(query)
        conv = result.scalar_one_or_none()

        if not conv:
            return []

        result = await self.session.execute(
            select(ConversationTurn)
            .where(ConversationTurn.conversation_id == conv.id)
            .order_by(desc(ConversationTurn.turn_number))
            .limit(limit)
        )
        turns = list(result.scalars().all())

        log.debug("history loaded", session_id=session_id, turns=len(turns))
        return turns[::-1]

    async def save_turn(
        self, session_id: str, turn: TurnData, user_id: Optional[UUID] = None
    ) -> ConversationTurn:
        """
        Save a conversation turn with optimistic retry.

        Retries on unique constraint violation to handle concurrent requests.

        Args:
            session_id: Session identifier
            turn: TurnData with turn information
            user_id: Optional user ID to associate with new conversation

        Returns:
            Created ConversationTurn

        Raises:
            IntegrityError: If unable to save after max retries
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                query = (
                    select(Conversation)
                    .where(Conversation.session_id == session_id)
                    .with_for_update()
                )
                if user_id is not None:
                    query = query.where(Conversation.user_id == user_id)

                result = await self.session.execute(query)
                conv = result.scalar_one_or_none()

                if not conv:
                    conv = Conversation(session_id=session_id, user_id=user_id)
                    self.session.add(conv)
                    await self.session.flush()

                # Lock the last turn to prevent concurrent inserts
                result = await self.session.execute(
                    select(ConversationTurn.turn_number)
                    .where(ConversationTurn.conversation_id == conv.id)
                    .order_by(ConversationTurn.turn_number.desc())
                    .limit(1)
                    .with_for_update()
                )
                max_turn = result.scalar_one_or_none()
                turn_number = (max_turn if max_turn is not None else -1) + 1

                ct = ConversationTurn(
                    conversation_id=conv.id,
                    turn_number=turn_number,
                    user_query=turn.user_query,
                    agent_response=turn.agent_response,
                    guardrail_score=turn.guardrail_score,
                    retrieval_attempts=turn.retrieval_attempts,
                    rewritten_query=turn.rewritten_query,
                    sources=turn.sources,
                    reasoning_steps=turn.reasoning_steps,
                    thinking_steps=turn.thinking_steps,
                    citations=turn.citations,
                    pending_confirmation=turn.pending_confirmation,
                    provider=turn.provider,
                    model=turn.model,
                )
                self.session.add(ct)
                await self.session.flush()
                await self.session.refresh(ct)

                log.debug("turn saved", session_id=session_id, turn_number=turn_number)
                return ct

            except IntegrityError:
                await self.session.rollback()
                self.session.expire_all()
                log.warning("turn save retry", session_id=session_id, attempt=attempt + 1)
                if attempt == max_retries - 1:
                    raise
                continue

        # Should never reach here, but satisfy type checker
        raise IntegrityError(
            "Failed to save turn after max retries", None, Exception("max retries")
        )

    async def complete_pending_turn(
        self,
        session_id: str,
        turn_number: int,
        agent_response: str,
        thinking_steps: list[dict] | None = None,
        sources: list[dict] | None = None,
        reasoning_steps: list[str] | None = None,
        citations: dict | None = None,
        user_id: Optional[UUID] = None,
    ) -> Optional[ConversationTurn]:
        """
        Complete a previously saved partial turn after HITL confirmation.

        Clears pending_confirmation and updates the agent response with final content.
        """
        query = select(Conversation).where(Conversation.session_id == session_id)
        if user_id is not None:
            query = query.where(Conversation.user_id == user_id)

        result = await self.session.execute(query)
        conv = result.scalar_one_or_none()
        if not conv:
            return None

        result = await self.session.execute(
            select(ConversationTurn)
            .where(
                ConversationTurn.conversation_id == conv.id,
                ConversationTurn.turn_number == turn_number,
            )
            .with_for_update()
        )
        ct = result.scalar_one_or_none()
        if not ct:
            return None

        ct.agent_response = agent_response
        ct.pending_confirmation = None
        if thinking_steps is not None:
            ct.thinking_steps = thinking_steps
        if sources is not None:
            ct.sources = sources
        if reasoning_steps is not None:
            ct.reasoning_steps = reasoning_steps
        if citations is not None:
            ct.citations = citations

        await self.session.flush()
        await self.session.refresh(ct)
        log.debug(
            "pending turn completed",
            session_id=session_id,
            turn_number=turn_number,
        )
        return ct

    async def has_pending_confirmation(
        self, session_id: str, user_id: Optional[UUID] = None
    ) -> bool:
        """Check whether the latest turn has an active pending_confirmation."""
        conv_query = select(Conversation.id).where(Conversation.session_id == session_id)
        if user_id is not None:
            conv_query = conv_query.where(Conversation.user_id == user_id)

        result = await self.session.execute(
            select(ConversationTurn.pending_confirmation)
            .where(
                ConversationTurn.conversation_id.in_(conv_query),
                ConversationTurn.pending_confirmation.isnot(None),
            )
            .order_by(ConversationTurn.turn_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_pending_turn(
        self, session_id: str, user_id: Optional[UUID] = None
    ) -> Optional[ConversationTurn]:
        """Get the latest turn with an active pending_confirmation for a session."""
        conv_query = select(Conversation.id).where(Conversation.session_id == session_id)
        if user_id is not None:
            conv_query = conv_query.where(Conversation.user_id == user_id)

        result = await self.session.execute(
            select(ConversationTurn)
            .where(
                ConversationTurn.conversation_id.in_(conv_query),
                ConversationTurn.pending_confirmation.isnot(None),
            )
            .order_by(ConversationTurn.turn_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def clear_pending_confirmation(
        self, session_id: str, turn_number: int, user_id: Optional[UUID] = None
    ) -> None:
        """Clear the pending_confirmation flag on a turn without updating other fields."""
        query = select(Conversation).where(Conversation.session_id == session_id)
        if user_id is not None:
            query = query.where(Conversation.user_id == user_id)

        result = await self.session.execute(query)
        conv = result.scalar_one_or_none()
        if not conv:
            return

        result = await self.session.execute(
            select(ConversationTurn)
            .where(
                ConversationTurn.conversation_id == conv.id,
                ConversationTurn.turn_number == turn_number,
            )
            .with_for_update()
        )
        ct = result.scalar_one_or_none()
        if not ct:
            return

        ct.pending_confirmation = None
        await self.session.flush()
        log.debug(
            "pending confirmation cleared",
            session_id=session_id,
            turn_number=turn_number,
        )

    async def update_title(
        self, session_id: str, title: str, user_id: Optional[UUID] = None
    ) -> None:
        """Update the title of a conversation."""
        query = select(Conversation).where(Conversation.session_id == session_id)
        if user_id is not None:
            query = query.where(Conversation.user_id == user_id)

        result = await self.session.execute(query)
        conv = result.scalar_one_or_none()
        if conv:
            conv.title = title
            await self.session.flush()

    async def delete(self, session_id: str, user_id: Optional[UUID] = None) -> bool:
        """
        Delete a conversation and all its turns.

        Args:
            session_id: Session identifier
            user_id: Optional user ID for ownership verification

        Returns:
            True if deleted, False if not found or not owned by user
        """
        query = select(Conversation).where(Conversation.session_id == session_id)
        if user_id is not None:
            query = query.where(Conversation.user_id == user_id)

        result = await self.session.execute(query)
        conv = result.scalar_one_or_none()

        if conv:
            await self.session.delete(conv)
            await self.session.flush()
            log.info("conversation deleted", session_id=session_id)
            return True

        return False

    async def get_by_session_id(
        self, session_id: str, user_id: Optional[UUID] = None
    ) -> Optional[Conversation]:
        """
        Get conversation by session ID.

        Args:
            session_id: Session identifier
            user_id: Optional user ID for ownership verification

        Returns:
            Conversation if found and owned by user, None otherwise
        """
        query = select(Conversation).where(Conversation.session_id == session_id)
        if user_id is not None:
            query = query.where(Conversation.user_id == user_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_turn_count(
        self, session_id: str, user_id: Optional[UUID] = None
    ) -> int:
        """
        Get the number of turns in a conversation.

        Args:
            session_id: Session identifier
            user_id: Optional user ID for ownership verification

        Returns:
            Number of turns
        """
        query = select(Conversation).where(Conversation.session_id == session_id)
        if user_id is not None:
            query = query.where(Conversation.user_id == user_id)

        result = await self.session.execute(query)
        conv = result.scalar_one_or_none()

        if not conv:
            return 0

        result = await self.session.execute(
            select(func.count()).where(ConversationTurn.conversation_id == conv.id)
        )
        return result.scalar_one() or 0

    async def get_all(
        self, offset: int = 0, limit: int = 20, user_id: Optional[UUID] = None
    ) -> Tuple[List[Conversation], int]:
        """
        Get paginated list of conversations with turn counts.

        Args:
            offset: Number of conversations to skip
            limit: Maximum conversations to return
            user_id: Optional user ID to filter by ownership

        Returns:
            Tuple of (list of Conversations, total count)
        """
        # Build queries with optional user_id filter
        count_query = select(func.count(Conversation.id))
        list_query = (
            select(Conversation)
            .options(selectinload(Conversation.turns))
            .order_by(desc(Conversation.updated_at))
            .offset(offset)
            .limit(limit)
        )

        if user_id is not None:
            count_query = count_query.where(Conversation.user_id == user_id)
            list_query = list_query.where(Conversation.user_id == user_id)

        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one() or 0

        # Get paginated conversations
        result = await self.session.execute(list_query)
        conversations = list(result.scalars().all())

        log.debug("conversations listed", total=total, returned=len(conversations))
        return conversations, total

    async def get_with_turns(
        self, session_id: str, user_id: Optional[UUID] = None
    ) -> Optional[Conversation]:
        """
        Get conversation with eager-loaded turns.

        Args:
            session_id: Session identifier
            user_id: Optional user ID for ownership verification

        Returns:
            Conversation with turns if found and owned by user, None otherwise
        """
        query = (
            select(Conversation)
            .options(selectinload(Conversation.turns))
            .where(Conversation.session_id == session_id)
        )
        if user_id is not None:
            query = query.where(Conversation.user_id == user_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()
