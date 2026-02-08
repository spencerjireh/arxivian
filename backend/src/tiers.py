"""User tier definitions and policy resolution.

Single source of truth for all tier-related logic: limits, capabilities,
model resolution, and system user identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from src.config import Settings

SYSTEM_USER_CLERK_ID = "system"


class UserTier(StrEnum):
    FREE = "free"
    PRO = "pro"


@dataclass(frozen=True, slots=True)
class TierPolicy:
    daily_chats: int | None  # None = unlimited
    search_slots: int
    can_ingest: bool
    can_search_arxiv: bool
    can_select_model: bool

    def resolve_model(self, requested: str | None, settings: Settings) -> str:
        """Return the model to use, enforcing tier restrictions."""
        if not self.can_select_model or not requested:
            return settings.default_llm_model
        if not settings.is_model_allowed(requested):
            from src.exceptions import InvalidModelError

            raise InvalidModelError(requested, "N/A", settings.get_allowed_models_list())
        return requested


ANONYMOUS_POLICY = TierPolicy(
    daily_chats=3,
    search_slots=0,
    can_ingest=False,
    can_search_arxiv=False,
    can_select_model=False,
)

TIER_POLICIES: dict[str, TierPolicy] = {
    UserTier.FREE: TierPolicy(
        daily_chats=20,
        search_slots=1,
        can_ingest=True,
        can_search_arxiv=True,
        can_select_model=False,
    ),
    UserTier.PRO: TierPolicy(
        daily_chats=None,
        search_slots=5,
        can_ingest=True,
        can_search_arxiv=True,
        can_select_model=True,
    ),
}


def get_policy(user: object | None) -> TierPolicy:
    """Resolve tier policy for a user (or None for anonymous)."""
    if user is None:
        return ANONYMOUS_POLICY
    tier = getattr(user, "tier", UserTier.FREE)
    return TIER_POLICIES.get(tier, TIER_POLICIES[UserTier.FREE])


# --- System user ID (loaded once at startup) ---

_system_user_id: UUID | None = None


def get_system_user_id() -> UUID:
    """Return the system user's DB id. Fails fast if called before init."""
    if _system_user_id is None:
        raise RuntimeError("System user not loaded -- call init_system_user() first")
    return _system_user_id


async def init_system_user(db: object) -> None:
    """Load the system user ID from the database. Call once at startup."""
    global _system_user_id
    from src.repositories.user_repository import UserRepository

    user = await UserRepository(db).get_by_clerk_id(SYSTEM_USER_CLERK_ID)  # type: ignore[arg-type]
    if user is None:
        raise RuntimeError(
            f"System user (clerk_id={SYSTEM_USER_CLERK_ID!r}) not found -- run migrations"
        )
    _system_user_id = user.id  # type: ignore[assignment]
