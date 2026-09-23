"""Users router -- /me (tier + usage) and the onboarding profile (ARX-9)."""

from fastapi import APIRouter

from src.dependencies import CurrentUserRequired, TierPolicyDep, UsageCounterRepoDep, UserRepoDep
from src.models.user import User
from src.repositories.usage_counter_repository import UsageCounterRepository
from src.schemas.users import FeedProfile, MeResponse, UpdatePreferencesRequest, UserPreferences
from src.tiers import TierPolicy
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

FEED_PROFILE_KEY = "feed_profile"


async def _build_me(
    user: User, policy: TierPolicy, usage_repo: UsageCounterRepository
) -> MeResponse:
    query_count = await usage_repo.get_today_query_count(user.id)
    profile = FeedProfile.from_user(user)
    has_profile = bool((user.preferences or {}).get(FEED_PROFILE_KEY))

    return MeResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        tier=user.tier,
        daily_chat_limit=policy.daily_chats,
        chats_used_today=query_count,
        preferences=UserPreferences(feed_profile=profile if has_profile else None),
        onboarded=profile.onboarded,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: CurrentUserRequired,
    policy: TierPolicyDep,
    usage_repo: UsageCounterRepoDep,
) -> MeResponse:
    """Get current user info including tier, limits, usage, and the feed profile."""
    return await _build_me(user, policy, usage_repo)


@router.patch("/me/preferences", response_model=MeResponse)
async def update_preferences(
    body: UpdatePreferencesRequest,
    user: CurrentUserRequired,
    policy: TierPolicyDep,
    usage_repo: UsageCounterRepoDep,
    user_repo: UserRepoDep,
) -> MeResponse:
    """Set the onboarding profile (categories, compute profile, keywords).

    Written under `preferences["feed_profile"]`; other keys in the JSONB (for example the
    system user's `arxiv_searches`) are preserved.
    """
    existing = FeedProfile.from_user(user)
    profile = FeedProfile(
        categories=body.categories,
        compute_profile=body.compute_profile,
        keywords=body.keywords,
        weights=existing.weights,
    )
    merged = {**(user.preferences or {}), FEED_PROFILE_KEY: profile.model_dump()}
    updated = await user_repo.update_preferences(user, merged)
    log.info(
        "feed_profile_updated",
        user_id=str(user.id),
        categories=body.categories,
        compute_profile=body.compute_profile,
    )
    return await _build_me(updated, policy, usage_repo)
