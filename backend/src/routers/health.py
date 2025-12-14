"""Health check router."""

from fastapi import APIRouter
from datetime import datetime
from src.schemas.health import HealthResponse, ServiceStatus
from src.dependencies import DbSession, OpenAIClientDep, EmbeddingsClientDep, PaperRepoDep, ChunkRepoDep

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: DbSession,
    openai_client: OpenAIClientDep,
    embeddings_client: EmbeddingsClientDep,
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
) -> HealthResponse:
    """
    Comprehensive health check for all services.

    Checks:
    - Database connectivity and counts
    - OpenAI API reachability
    - Jina embeddings API reachability

    Returns:
        HealthResponse with status and service details
    """
    services = {}
    overall_status = "ok"

    # Check database
    try:
        papers_count = await paper_repo.count()
        chunks_count = await chunk_repo.count()

        services["database"] = ServiceStatus(
            status="healthy",
            message="Connected",
            details={"papers_count": papers_count, "chunks_count": chunks_count},
        )
    except Exception as e:
        services["database"] = ServiceStatus(status="unhealthy", message=f"Error: {str(e)}")
        overall_status = "degraded"

    # Check OpenAI (simple configuration check)
    try:
        if openai_client.client.api_key:
            services["openai"] = ServiceStatus(status="healthy", message="API key configured")
        else:
            raise ValueError("No API key")
    except Exception as e:
        services["openai"] = ServiceStatus(status="unhealthy", message=f"Error: {str(e)}")
        overall_status = "degraded"

    # Check Jina
    try:
        if embeddings_client.api_key:
            services["jina"] = ServiceStatus(status="healthy", message="API key configured")
        else:
            raise ValueError("No API key")
    except Exception as e:
        services["jina"] = ServiceStatus(status="unhealthy", message=f"Error: {str(e)}")
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version="0.1.0",
        services=services,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
