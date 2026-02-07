"""Ops operations router."""

from fastapi import APIRouter

from src.schemas.ops import CleanupResponse, OrphanedPaper
from src.dependencies import PaperRepoDep, DbSession, CurrentUserRequired
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/ops", tags=["Ops"])


# TODO: restrict to admin role once RBAC is implemented
@router.post("/cleanup", response_model=CleanupResponse)
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
