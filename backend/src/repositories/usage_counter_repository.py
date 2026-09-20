"""Repository for daily usage counter operations."""

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.usage_counter import UsageCounter
from src.utils.logger import get_logger

log = get_logger(__name__)


class UsageCounterRepository:
    """Repository for atomic daily usage counter operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_today_query_count(self, user_id: str | UUID) -> int:
        """Get today's query count for a user. Returns 0 if no row exists."""
        result = await self.session.execute(
            select(UsageCounter.query_count).where(
                UsageCounter.user_id == user_id,
                UsageCounter.usage_date == func.current_date(),
            )
        )
        row = result.scalar_one_or_none()
        return row if row is not None else 0

    async def increment_query_count(self, user_id: str | UUID) -> int:
        """Atomically increment today's query count via UPSERT.

        Creates the row if it doesn't exist. Returns the new count.
        """
        result = await self.session.execute(
            text("""
                INSERT INTO usage_counters (id, user_id, usage_date, query_count)
                VALUES (gen_random_uuid(), :user_id, CURRENT_DATE, 1)
                ON CONFLICT (user_id, usage_date)
                DO UPDATE SET query_count = usage_counters.query_count + 1,
                             updated_at = now()
                RETURNING query_count
            """),
            {"user_id": str(user_id)},
        )
        count = result.scalar_one()
        log.debug("query count incremented", user_id=str(user_id), count=count)
        return count
