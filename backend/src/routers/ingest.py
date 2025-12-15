"""Paper ingestion router."""

from fastapi import APIRouter

from src.schemas.ingest import IngestRequest, IngestResponse
from src.dependencies import DbSession, IngestServiceDep

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_papers(
    request: IngestRequest,
    db: DbSession,
    ingest_service: IngestServiceDep,
) -> IngestResponse:
    """
    Ingest papers from arXiv.

    Delegates to IngestService for business logic.

    Args:
        request: Ingestion parameters
        db: Database session
        ingest_service: Injected ingest service

    Returns:
        IngestResponse with processing summary
    """
    # Delegate to service layer
    # Transaction management handled by middleware
    response = await ingest_service.ingest_papers(request)

    # Commit transaction explicitly for ingestion
    # (since it may have partial success with errors)
    await db.commit()

    return response
