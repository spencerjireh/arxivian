"""User schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

if TYPE_CHECKING:
    from src.models.user import User

ComputeProfile = Literal["laptop", "single_gpu", "cloud"]


class FeedProfile(BaseModel):
    """The onboarding profile stored under `users.preferences["feed_profile"]`.

    Kept in its own key so it never collides with the system user's `arxiv_searches`.
    `weights` is reserved for per-user composite weights and is not settable via the API in
    v1 (SPE-273 sets categories / compute_profile / keywords).
    """

    model_config = ConfigDict(extra="ignore")

    categories: list[str] = Field(default_factory=list, max_length=20)
    compute_profile: ComputeProfile | None = None
    keywords: list[str] = Field(default_factory=list, max_length=20)
    weights: dict[str, float] | None = Field(
        default=None, description="Per-user composite weights; None means the defaults"
    )

    @classmethod
    def from_user(cls, user: User) -> FeedProfile:
        """Read the profile off a user row; malformed or missing payloads read as empty."""
        raw = (user.preferences or {}).get("feed_profile") or {}
        try:
            return cls.model_validate(raw)
        except ValidationError:
            return cls()

    @property
    def onboarded(self) -> bool:
        return bool(self.categories) and self.compute_profile is not None


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
