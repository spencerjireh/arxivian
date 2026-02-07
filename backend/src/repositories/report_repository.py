"""Repository for Report model operations."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.report import Report
from src.utils.logger import get_logger

log = get_logger(__name__)


class ReportRepository:
    """Repository for Report CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        report_type: str,
        period_start: datetime,
        period_end: datetime,
        data: dict,
    ) -> Report:
        """Create a new report record."""
        report = Report(
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            data=data,
        )
        self.session.add(report)
        await self.session.flush()
        await self.session.refresh(report)
        log.debug("report_created", report_type=report_type)
        return report

    async def get_by_id(self, report_id: UUID) -> Optional[Report]:
        """Get report by ID."""
        result = await self.session.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()

    async def list_reports(self, limit: int = 20, offset: int = 0) -> tuple[list[Report], int]:
        """List reports with pagination, newest first."""
        count_result = await self.session.execute(select(func.count()).select_from(Report))
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(Report).order_by(Report.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
