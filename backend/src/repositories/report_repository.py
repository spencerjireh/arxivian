"""Repository for Report model operations."""

from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.models.report import Report
from src.tiers import get_system_user_id
from src.utils.logger import get_logger

log = get_logger(__name__)


class ReportRepository:
    """Repository for Report CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _ownership_filter(self, user_id: UUID | None):
        """System content for anon, system + own for authenticated."""
        system_id = get_system_user_id()
        if user_id is None:
            return Report.user_id == system_id
        return Report.user_id.in_([user_id, system_id])

    async def create(
        self,
        user_id: UUID,
        report_type: str,
        period_start: datetime,
        period_end: datetime,
        data: dict,
    ) -> Report:
        """Create a new report record."""
        report = Report(
            user_id=user_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            data=data,
        )
        self.session.add(report)
        await self.session.flush()
        await self.session.refresh(report)
        log.debug("report_created", report_type=report_type, user_id=str(user_id))
        return report

    async def get_by_id(
        self, report_id: UUID, user_id: UUID | None = None
    ) -> Optional[Report]:
        """Get report by ID, scoped to user + system ownership."""
        stmt = select(Report).where(Report.id == report_id)
        stmt = stmt.where(self._ownership_filter(user_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_reports(
        self, user_id: UUID | None = None, limit: int = 20, offset: int = 0
    ) -> tuple[list[Report], int]:
        """List reports with pagination, newest first. Scoped to user + system."""
        ownership = self._ownership_filter(user_id)

        count_result = await self.session.execute(
            select(func.count()).select_from(Report).where(ownership)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(Report)
            .where(ownership)
            .order_by(Report.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_or_create_daily_report(
        self, user_id: UUID, report_date: date
    ) -> Report:
        """Get existing daily report for user or create a new one."""
        start = datetime(
            report_date.year, report_date.month, report_date.day,
            tzinfo=timezone.utc,
        )
        end = datetime(
            report_date.year, report_date.month, report_date.day,
            23, 59, 59, tzinfo=timezone.utc,
        )

        result = await self.session.execute(
            select(Report).where(
                Report.user_id == user_id,
                Report.report_type == "daily_ingest",
                Report.period_start == start,
            )
        )
        report = result.scalar_one_or_none()

        if report is not None:
            return report

        try:
            async with self.session.begin_nested():
                return await self.create(
                    user_id=user_id,
                    report_type="daily_ingest",
                    period_start=start,
                    period_end=end,
                    data={"ingestions": []},
                )
        except IntegrityError:
            result = await self.session.execute(
                select(Report).where(
                    Report.user_id == user_id,
                    Report.report_type == "daily_ingest",
                    Report.period_start == start,
                )
            )
            return result.scalar_one()

    async def append_ingest_result(
        self,
        report: Report,
        search_name: str,
        query: str,
        result: dict,
    ) -> None:
        """Append an ingestion result to a report's data."""
        report.data["ingestions"].append(
            {
                "search_name": search_name,
                "query": query,
                "papers_processed": result.get("papers_processed", 0),
                "chunks_created": result.get("chunks_created", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        flag_modified(report, "data")
        await self.session.flush()
