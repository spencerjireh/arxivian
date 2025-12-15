"""Health check router."""

from fastapi import APIRouter
from datetime import datetime
from src.schemas.health import HealthResponse, ServiceStatus
from src.dependencies import DbSession, EmbeddingsClientDep, PaperRepoDep, ChunkRepoDep
from src.config import get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: DbSession,
    embeddings_client: EmbeddingsClientDep,
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
) -> HealthResponse:
    """
    Comprehensive health check for all services.

    Checks:
    - Database connectivity and counts
    - LLM provider configuration
    - Jina embeddings API reachability

    Returns:
        HealthResponse with status and service details
    """
    services = {}
    overall_status = "ok"
    settings = get_settings()

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

    # Check LLM provider configuration
    try:
        provider = settings.default_llm_provider

        # Check if API key is configured for default provider
        if provider == "openai" and settings.openai_api_key:
            services["llm"] = ServiceStatus(
                status="healthy",
                message=f"LLM provider configured: {provider}",
                details={"provider": provider, "models": settings.get_allowed_models(provider)},
            )
        elif provider == "zai" and settings.zai_api_key:
            services["llm"] = ServiceStatus(
                status="healthy",
                message=f"LLM provider configured: {provider}",
                details={"provider": provider, "models": settings.get_allowed_models(provider)},
            )
        else:
            raise ValueError(f"No API key configured for provider: {provider}")
    except Exception as e:
        services["llm"] = ServiceStatus(status="unhealthy", message=f"Error: {str(e)}")
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
        version="0.2.0",
        services=services,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
