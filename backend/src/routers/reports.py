"""User reports router."""

from uuid import UUID

from fastapi import APIRouter, Query

from src.schemas.reports import ReportResponse, ReportListResponse
from src.dependencies import CurrentUserOptional, ReportRepoDep
from src.exceptions import ResourceNotFoundError
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/", response_model=ReportListResponse)
async def list_reports(
    current_user: CurrentUserOptional,
    report_repo: ReportRepoDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ReportListResponse:
    """List reports. Anonymous sees system reports, signed-in sees system + own."""
    user_id = current_user.id if current_user else None
    reports, total = await report_repo.list_reports(
        user_id=user_id, limit=limit, offset=offset
    )

    return ReportListResponse(
        reports=[ReportResponse.model_validate(r, from_attributes=True) for r in reports],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: CurrentUserOptional,
    report_repo: ReportRepoDep,
) -> ReportResponse:
    """Get a specific report by ID."""
    user_id = current_user.id if current_user else None
    report = await report_repo.get_by_id(report_id, user_id=user_id)
    if report is None:
        raise ResourceNotFoundError("Report", str(report_id))

    return ReportResponse.model_validate(report, from_attributes=True)
