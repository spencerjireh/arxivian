"""Paper ingestion router."""

from fastapi import APIRouter, HTTPException

from src.schemas.ingest import IngestRequest, IngestResponse
from src.dependencies import (
    DbSession,
    IngestServiceDep,
    CurrentUserRequired,
    IngestUsageCheck,
    UsageCounterRepoDep,
)
from src.utils.idempotency import idempotency_store

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_papers(
    request: IngestRequest,
    db: DbSession,
    ingest_service: IngestServiceDep,
    current_user: CurrentUserRequired,
    usage_repo: UsageCounterRepoDep,
    _usage_check: IngestUsageCheck,
) -> IngestResponse:
    """
    Ingest papers from arXiv.

    Delegates to IngestService for business logic. Supports idempotency
    via optional idempotency_key to prevent duplicate processing.

    Args:
        request: Ingestion parameters
        db: Database session
        ingest_service: Injected ingest service

    Returns:
        IngestResponse with processing summary

    Raises:
        HTTPException 409: If a request with the same idempotency key is in progress
    """
    # Handle idempotency if key provided
    if request.idempotency_key:
        existing = await idempotency_store.acquire(request.idempotency_key)

        if existing:
            if existing.status == "in_progress":
                raise HTTPException(
                    status_code=409,
                    detail="Request with this idempotency key is already in progress",
                )
            elif existing.status == "completed" and existing.response:
                # Return cached response
                return existing.response

    try:
        # Delegate to service layer
        response = await ingest_service.ingest_papers(request)

        # Increment usage counter before commit
        await usage_repo.increment_ingest_count(current_user.id)

        # Commit transaction explicitly for ingestion
        # (since it may have partial success with errors)
        await db.commit()

        # Cache successful response
        if request.idempotency_key:
            await idempotency_store.complete(request.idempotency_key, response)

        return response

    except Exception:
        # Ensure rollback if exception occurs before commit
        await db.rollback()
        # Release idempotency key on failure to allow retry
        if request.idempotency_key:
            await idempotency_store.fail(request.idempotency_key)
        raise
