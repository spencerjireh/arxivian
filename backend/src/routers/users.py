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
    ingest_count = await usage_repo.get_today_ingest_count(user.id)

    return MeResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        tier=user.tier,
        daily_chat_limit=policy.daily_chats,
        chats_used_today=query_count,
        can_adjust_settings=policy.can_adjust_settings,
        daily_ingest_limit=policy.daily_ingests,
        ingests_used_today=ingest_count,
        can_view_execution_details=policy.can_view_execution_details,
    )
