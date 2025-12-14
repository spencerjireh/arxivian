"""Search router."""

from fastapi import APIRouter
from time import time
from src.schemas.search import SearchRequest, SearchResponse
from src.schemas.common import ChunkInfo
from src.dependencies import SearchServiceDep

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, search_service: SearchServiceDep) -> SearchResponse:
    """
    Hybrid search endpoint with vector + full-text + RRF.

    Supports three modes:
    - vector: Pure semantic search
    - fulltext: Pure keyword search
    - hybrid: RRF fusion (recommended)

    Args:
        request: Search parameters
        search_service: Injected search service

    Returns:
        SearchResponse with ranked results
    """
    start_time = time()

    # Execute search
    results = await search_service.hybrid_search(
        query=request.query,
        top_k=request.top_k,
        mode=request.search_mode,
        min_score=request.min_score,
    )

    # Convert to response format
    chunk_infos = [
        ChunkInfo(
            chunk_id=str(r.chunk_id),
            arxiv_id=r.arxiv_id,
            title=r.title,
            chunk_text=r.chunk_text,
            section_name=r.section_name,
            score=r.score,
            vector_score=r.vector_score if hasattr(r, "vector_score") else None,
            text_score=r.text_score if hasattr(r, "text_score") else None,
        )
        for r in results
    ]

    execution_time = (time() - start_time) * 1000  # Convert to ms

    return SearchResponse(
        query=request.query,
        total=len(chunk_infos),
        results=chunk_infos,
        search_mode=request.search_mode,
        execution_time_ms=execution_time,
    )
