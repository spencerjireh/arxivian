"""User tier definitions and policy resolution.

Single source of truth for tier limits and the system user identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from src.repositories.user_repository import UserRepository

if TYPE_CHECKING:
    from src.models.user import User

SYSTEM_USER_CLERK_ID = "system"


class UserTier(StrEnum):
    FREE = "free"
    PRO = "pro"


@dataclass(frozen=True, slots=True)
class TierPolicy:
    daily_chats: int | None  # None = unlimited


TIER_POLICIES: dict[str, TierPolicy] = {
    UserTier.FREE: TierPolicy(daily_chats=10),
    UserTier.PRO: TierPolicy(daily_chats=None),
}


def get_policy(user: User) -> TierPolicy:
    """Resolve tier policy for a user."""
    return TIER_POLICIES.get(user.tier, TIER_POLICIES[UserTier.FREE])


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

    user = await UserRepository(db).get_by_clerk_id(SYSTEM_USER_CLERK_ID)  # type: ignore[arg-type]
    if user is None:
        raise RuntimeError(
            f"System user (clerk_id={SYSTEM_USER_CLERK_ID!r}) not found -- run migrations"
        )
    _system_user_id = user.id  # type: ignore[assignment]
