"""Users router -- /me endpoint for tier and usage info."""

from fastapi import APIRouter

from src.schemas.users import MeResponse
from src.dependencies import CurrentUserRequired, TierPolicyDep, UsageCounterRepoDep

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: CurrentUserRequired,
    policy: TierPolicyDep,
    usage_repo: UsageCounterRepoDep,
) -> MeResponse:
    """Get current user info including tier, limits, and usage."""
    query_count = await usage_repo.get_today_query_count(user.id)
    searches = (user.preferences or {}).get("arxiv_searches", [])
    enabled = sum(1 for s in searches if s.get("enabled", True))

    return MeResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        tier=user.tier,
        daily_chat_limit=policy.daily_chats,
        chats_used_today=query_count,
        search_slot_limit=policy.search_slots,
        search_slots_used=enabled,
        can_select_model=policy.can_select_model,
    )
