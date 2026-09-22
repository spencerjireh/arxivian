"""Response schemas for GET/DELETE /conversations (routers/conversations.py)."""

from datetime import datetime

from pydantic import ConfigDict, Field

from src.schemas.base import ResponseModel
from src.schemas.stream import CitationsEventData, SourceInfo


class ConversationTurnResponse(ResponseModel):
    """Response schema for a single conversation turn."""

    turn_number: int
    user_query: str
    agent_response: str
    provider: str
    model: str
    guardrail_score: int | None = None
    retrieval_attempts: int = 1
    rewritten_query: str | None = None
    sources: list[SourceInfo] | None = None
    reasoning_steps: list[str] | None = None
    citations: CitationsEventData | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationListItem(ResponseModel):
    """Summary item for conversation list."""

    session_id: str
    title: str | None = None
    turn_count: int
    created_at: datetime
    updated_at: datetime
    last_query: str | None = Field(None, description="Preview of last user message")
    arxiv_id: str | None = Field(None, description="Paper this thread is scoped to, if any")


class ConversationListResponse(ResponseModel):
    """Paginated list of conversations."""

    total: int
    offset: int
    limit: int
    conversations: list[ConversationListItem]


class ConversationDetailResponse(ResponseModel):
    """Full conversation with all turns."""

    session_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    arxiv_id: str | None = Field(None, description="Paper this thread is scoped to, if any")
    turns: list[ConversationTurnResponse]


class DeleteConversationResponse(ResponseModel):
    """Response after deleting a conversation."""

    session_id: str
    turns_deleted: int
