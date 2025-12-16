"""Conversation schemas for multi-turn memory."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class ConversationMessage(TypedDict):
    """A single message in a conversation."""

    role: Literal["user", "assistant"]
    content: str


@dataclass
class TurnData:
    """Data for saving a conversation turn."""

    user_query: str
    agent_response: str
    provider: str
    model: str
    guardrail_score: int | None = None
    retrieval_attempts: int = 1
    rewritten_query: str | None = None
    sources: list[dict] | None = None
    reasoning_steps: list[str] | None = None


# API Response Schemas


class ConversationTurnResponse(BaseModel):
    """Response schema for a single conversation turn."""

    turn_number: int
    user_query: str
    agent_response: str
    provider: str
    model: str
    guardrail_score: int | None = None
    retrieval_attempts: int = 1
    rewritten_query: str | None = None
    sources: list[dict] | None = None
    reasoning_steps: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationListItem(BaseModel):
    """Summary item for conversation list."""

    session_id: str
    turn_count: int
    created_at: datetime
    updated_at: datetime
    last_query: str | None = Field(None, description="Preview of last user message")


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""

    total: int
    offset: int
    limit: int
    conversations: list[ConversationListItem]


class ConversationDetailResponse(BaseModel):
    """Full conversation with all turns."""

    session_id: str
    created_at: datetime
    updated_at: datetime
    turns: list[ConversationTurnResponse]


class DeleteConversationResponse(BaseModel):
    """Response after deleting a conversation."""

    session_id: str
    turns_deleted: int
