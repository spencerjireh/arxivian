"""User schemas."""

from uuid import UUID

from pydantic import BaseModel


class MeResponse(BaseModel):
    """Response for /users/me endpoint."""

    id: UUID
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    tier: str
    daily_chat_limit: int | None = None  # None = unlimited
    chats_used_today: int
    can_adjust_settings: bool
    daily_ingest_limit: int | None = None  # None = unlimited
    ingests_used_today: int = 0
    can_view_execution_details: bool = False
