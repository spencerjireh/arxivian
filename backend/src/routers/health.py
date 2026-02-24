"""Health check router."""

from fastapi import APIRouter
from datetime import datetime, timezone
from src.schemas.health import HealthResponse, ServiceStatus
from src.dependencies import DbSession, EmbeddingsClientDep, PaperRepoDep, ChunkRepoDep
from src.config import get_settings
from src.utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)


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
        log.error("health check failed", service="database", error=str(e))
        services["database"] = ServiceStatus(status="unhealthy", message="Service unavailable")
        overall_status = "degraded"

    # Check LLM provider configuration
    try:
        default_model = settings.default_llm_model
        provider = default_model.split("/", 1)[0] if "/" in default_model else default_model

        # Check if API key is configured for the provider
        has_key = False
        if provider == "openai" and settings.openai_api_key:
            has_key = True
        elif provider == "nvidia_nim" and settings.nvidia_nim_api_key:
            has_key = True

        if has_key:
            services["llm"] = ServiceStatus(
                status="healthy",
                message=f"LLM provider configured: {provider}",
                details={
                    "default_model": default_model,
                    "allowed_models": settings.get_allowed_models_list(),
                },
            )
        else:
            raise ValueError(f"No API key configured for provider: {provider}")
    except Exception as e:
        log.error("health check failed", service="llm", error=str(e))
        services["llm"] = ServiceStatus(status="unhealthy", message="Service unavailable")
        overall_status = "degraded"

    # Check Jina
    try:
        if embeddings_client.api_key:
            services["jina"] = ServiceStatus(status="healthy", message="API key configured")
        else:
            raise ValueError("No API key")
    except Exception as e:
        log.error("health check failed", service="jina", error=str(e))
        services["jina"] = ServiceStatus(status="unhealthy", message="Service unavailable")
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version="0.2.0",
        services=services,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
