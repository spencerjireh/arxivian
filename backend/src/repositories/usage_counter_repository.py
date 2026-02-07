"""Repository for daily usage counter operations."""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.usage_counter import UsageCounter
from src.utils.logger import get_logger

log = get_logger(__name__)


class UsageCounterRepository:
    """Repository for atomic daily usage counter operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_today_counts(self, user_id: str) -> tuple[int, int]:
        """Get today's query and ingest counts for a user.

        Returns (0, 0) if no row exists yet for today.
        """
        result = await self.session.execute(
            select(UsageCounter.query_count, UsageCounter.ingest_count).where(
                UsageCounter.user_id == user_id,
                UsageCounter.usage_date == func.current_date(),
            )
        )
        row = result.one_or_none()
        if row is None:
            return (0, 0)
        return (row.query_count, row.ingest_count)

    async def increment_query_count(self, user_id: str) -> int:
        """Atomically increment today's query count via UPSERT.

        Creates the row if it doesn't exist. Returns the new count.
        """
        result = await self.session.execute(
            text("""
                INSERT INTO usage_counters (id, user_id, usage_date, query_count, ingest_count)
                VALUES (gen_random_uuid(), :user_id, CURRENT_DATE, 1, 0)
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

    async def increment_ingest_count(self, user_id: str) -> int:
        """Atomically increment today's ingest count via UPSERT.

        Creates the row if it doesn't exist. Returns the new count.
        """
        result = await self.session.execute(
            text("""
                INSERT INTO usage_counters (id, user_id, usage_date, ingest_count, query_count)
                VALUES (gen_random_uuid(), :user_id, CURRENT_DATE, 1, 0)
                ON CONFLICT (user_id, usage_date)
                DO UPDATE SET ingest_count = usage_counters.ingest_count + 1,
                             updated_at = now()
                RETURNING ingest_count
            """),
            {"user_id": str(user_id)},
        )
        count = result.scalar_one()
        log.debug("ingest count incremented", user_id=str(user_id), count=count)
        return count
