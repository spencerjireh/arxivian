"""Response schemas for GET/DELETE /conversations (routers/conversations.py)."""

from datetime import datetime

from pydantic import BaseModel, Field


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
    citations: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationListItem(BaseModel):
    """Summary item for conversation list."""

    session_id: str
    title: str | None = None
    turn_count: int
    created_at: datetime
    updated_at: datetime
    last_query: str | None = Field(None, description="Preview of last user message")
    arxiv_id: str | None = Field(None, description="Paper this thread is scoped to, if any")


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""

    total: int
    offset: int
    limit: int
    conversations: list[ConversationListItem]


class ConversationDetailResponse(BaseModel):
    """Full conversation with all turns."""

    session_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    arxiv_id: str | None = Field(None, description="Paper this thread is scoped to, if any")
    turns: list[ConversationTurnResponse]


class DeleteConversationResponse(BaseModel):
    """Response after deleting a conversation."""

    session_id: str
    turns_deleted: int
