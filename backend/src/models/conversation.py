"""Conversation models for multi-turn memory."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Integer, ForeignKey, TIMESTAMP, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from src.models.user import User


class Conversation(Base):
    """A conversation session."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata_", JSONB)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship to user
    user: Mapped[User | None] = relationship("User", back_populates="conversations")

    # Relationship to turns
    turns: Mapped[list[ConversationTurn]] = relationship(
        "ConversationTurn",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationTurn.turn_number",
    )

    def __repr__(self):
        return f"<Conversation(session_id='{self.session_id}')>"


class ConversationTurn(Base):
    """A single turn in a conversation."""

    __tablename__ = "conversation_turns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    turn_number: Mapped[int] = mapped_column(Integer)
    user_query: Mapped[str] = mapped_column(Text)
    agent_response: Mapped[str] = mapped_column(Text)
    guardrail_score: Mapped[int | None] = mapped_column(Integer)
    retrieval_attempts: Mapped[int] = mapped_column(Integer, default=1)
    rewritten_query: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list | None] = mapped_column(JSONB)
    reasoning_steps: Mapped[list | None] = mapped_column(JSONB)
    thinking_steps: Mapped[list | None] = mapped_column(JSONB)
    citations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pending_confirmation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationship to conversation
    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="turns")

    # Unique constraint on (conversation_id, turn_number)
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "turn_number",
            name="uq_conversation_turns_conversation_id_turn_number",
        ),
    )

    def __repr__(self):
        return (
            f"<ConversationTurn(conversation_id='{self.conversation_id}', turn={self.turn_number})>"
        )
