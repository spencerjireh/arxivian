"""Admin operations router."""

from uuid import UUID

from fastapi import APIRouter, Query

from src.schemas.admin import CleanupResponse, OrphanedPaper
from src.schemas.reports import ReportResponse, ReportListResponse
from src.dependencies import PaperRepoDep, DbSession, CurrentUserRequired, ReportRepoDep
from src.exceptions import ResourceNotFoundError
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter()


@router.post("/admin/cleanup", response_model=CleanupResponse)
async def cleanup_orphaned_records(
    paper_repo: PaperRepoDep,
    db: DbSession,
    current_user: CurrentUserRequired,
) -> CleanupResponse:
    """
    Clean up orphaned database records.

    Finds papers that are marked as processed but have no associated chunks,
    which indicates a failed ingestion. Deletes these orphaned papers.

    Returns:
        CleanupResponse with summary of deleted records
    """
    log.info("starting orphaned record cleanup")

    # Find orphaned papers (processed but no chunks)
    orphaned = await paper_repo.get_orphaned_papers()

    deleted_papers = []
    for paper in orphaned:
        arxiv_id = str(paper.arxiv_id)
        title = str(paper.title) if paper.title else ""
        deleted_papers.append(
            OrphanedPaper(
                arxiv_id=arxiv_id,
                title=title[:100],
                paper_id=str(paper.id),
            )
        )
        await paper_repo.delete(str(paper.id))
        log.debug("deleted orphaned paper", arxiv_id=arxiv_id)

    await db.commit()

    log.info(
        "orphaned record cleanup complete",
        found=len(orphaned),
        deleted=len(deleted_papers),
    )

    return CleanupResponse(
        orphaned_papers_found=len(orphaned),
        papers_deleted=len(deleted_papers),
        deleted_papers=deleted_papers,
    )


@router.get("/admin/reports", response_model=ReportListResponse)
async def list_reports(
    current_user: CurrentUserRequired,
    report_repo: ReportRepoDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ReportListResponse:
    """List generated reports."""
    reports, total = await report_repo.list_reports(limit=limit, offset=offset)

    return ReportListResponse(
        reports=[ReportResponse.model_validate(r, from_attributes=True) for r in reports],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: CurrentUserRequired,
    report_repo: ReportRepoDep,
) -> ReportResponse:
    """Get a specific report by ID."""
    report = await report_repo.get_by_id(report_id)
    if report is None:
        raise ResourceNotFoundError("Report", str(report_id))

    return ReportResponse.model_validate(report, from_attributes=True)
