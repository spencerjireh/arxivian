"""User schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class MeResponse(BaseModel):
    """Response for /users/me endpoint."""

    id: UUID
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tier: str
    daily_chat_limit: Optional[int] = None  # None = unlimited
    chats_used_today: int
    search_slot_limit: int
    search_slots_used: int
    can_select_model: bool
