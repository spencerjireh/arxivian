"""Repository for Conversation model operations."""

from typing import Optional, List
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from src.models.conversation import Conversation, ConversationTurn
from src.schemas.conversation import TurnData
from src.utils.logger import get_logger

log = get_logger(__name__)


class ConversationRepository:
    """Repository for conversation CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, session_id: str) -> Conversation:
        """
        Get existing conversation or create new one.

        Args:
            session_id: Unique session identifier

        Returns:
            Conversation instance
        """
        result = await self.session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conv = result.scalar_one_or_none()

        if not conv:
            conv = Conversation(session_id=session_id)
            self.session.add(conv)
            await self.session.commit()
            await self.session.refresh(conv)
            log.debug("conversation created", session_id=session_id)
        else:
            log.debug("conversation found", session_id=session_id)

        return conv

    async def get_history(self, session_id: str, limit: int = 5) -> List[ConversationTurn]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of turns to return

        Returns:
            List of ConversationTurn in chronological order
        """
        result = await self.session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
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

    async def save_turn(self, session_id: str, turn: TurnData) -> ConversationTurn:
        """
        Save a conversation turn with optimistic retry.

        Retries on unique constraint violation to handle concurrent requests.

        Args:
            session_id: Session identifier
            turn: TurnData with turn information

        Returns:
            Created ConversationTurn

        Raises:
            IntegrityError: If unable to save after max retries
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                result = await self.session.execute(
                    select(Conversation)
                    .where(Conversation.session_id == session_id)
                    .with_for_update()
                )
                conv = result.scalar_one_or_none()

                if not conv:
                    conv = Conversation(session_id=session_id)
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
                    provider=turn.provider,
                    model=turn.model,
                )
                self.session.add(ct)
                await self.session.commit()
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
        raise IntegrityError("Failed to save turn after max retries", None, None)

    async def delete(self, session_id: str) -> bool:
        """
        Delete a conversation and all its turns.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conv = result.scalar_one_or_none()

        if conv:
            await self.session.delete(conv)
            await self.session.commit()
            log.info("conversation deleted", session_id=session_id)
            return True

        return False

    async def get_by_session_id(self, session_id: str) -> Optional[Conversation]:
        """
        Get conversation by session ID.

        Args:
            session_id: Session identifier

        Returns:
            Conversation if found, None otherwise
        """
        result = await self.session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_turn_count(self, session_id: str) -> int:
        """
        Get the number of turns in a conversation.

        Args:
            session_id: Session identifier

        Returns:
            Number of turns
        """
        result = await self.session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conv = result.scalar_one_or_none()

        if not conv:
            return 0

        result = await self.session.execute(
            select(func.count()).where(ConversationTurn.conversation_id == conv.id)
        )
        return result.scalar_one() or 0
