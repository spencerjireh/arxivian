"""User schemas."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from src.schemas.base import ResponseModel
from src.tiers import UserTier

if TYPE_CHECKING:
    from src.models.user import User

ComputeProfile = Literal["laptop", "single_gpu", "cloud"]


class FeedProfile(ResponseModel):
    """The onboarding profile stored under `users.preferences["feed_profile"]`.

    Kept in its own key so it never collides with the system user's `arxiv_searches`.
    `weights` is reserved for per-user composite weights and is not settable via the API in
    v1 (ARX-9 sets categories / compute_profile / keywords).
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


class UserPreferences(ResponseModel):
    """The user-facing slice of `users.preferences` (the system user's keys are omitted)."""

    feed_profile: FeedProfile | None = None


_CATEGORY_RE = re.compile(r"^[a-z\-]+(\.[A-Za-z\-]+)?$")
_MAX_KEYWORD_LENGTH = 50


class UpdatePreferencesRequest(BaseModel):
    """PATCH /users/me/preferences body: the onboarding profile (ONBOARD-1)."""

    model_config = ConfigDict(extra="forbid")

    categories: list[str] = Field(..., min_length=1, max_length=20)
    compute_profile: ComputeProfile
    keywords: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("categories")
    @classmethod
    def _categories(cls, value: list[str]) -> list[str]:
        cleaned = sorted({c.strip() for c in value if c.strip()})
        if not cleaned:
            raise ValueError("at least one category is required")
        for category in cleaned:
            if not _CATEGORY_RE.fullmatch(category):
                raise ValueError(f"invalid arXiv category '{category}'")
        return cleaned

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, value: list[str]) -> list[str]:
        cleaned = [k.strip().lower() for k in value if k.strip()]
        if any(len(k) > _MAX_KEYWORD_LENGTH for k in cleaned):
            raise ValueError(f"keywords must be at most {_MAX_KEYWORD_LENGTH} characters")
        return list(dict.fromkeys(cleaned))


class MeResponse(ResponseModel):
    """Response for /users/me endpoint."""

    id: UUID
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    tier: UserTier
    daily_chat_limit: int | None = None  # None = unlimited
    chats_used_today: int
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    onboarded: bool = False
