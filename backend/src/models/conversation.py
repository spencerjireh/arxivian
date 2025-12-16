"""Conversation models for multi-turn memory."""

import uuid
from sqlalchemy import Column, String, Text, Integer, ForeignKey, TIMESTAMP, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.database import Base


class Conversation(Base):
    """A conversation session."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    metadata_ = Column("metadata_", JSONB, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship to turns
    turns = relationship(
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_number = Column(Integer, nullable=False)
    user_query = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)
    guardrail_score = Column(Integer, nullable=True)
    retrieval_attempts = Column(Integer, default=1)
    rewritten_query = Column(Text, nullable=True)
    sources = Column(JSONB, nullable=True)
    reasoning_steps = Column(JSONB, nullable=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="turns")

    # Unique constraint on (conversation_id, turn_number)
    __table_args__ = (
        UniqueConstraint("conversation_id", "turn_number", name="uq_conversation_turns_conversation_id_turn_number"),
    )

    def __repr__(self):
        return f"<ConversationTurn(conversation_id='{self.conversation_id}', turn={self.turn_number})>"
