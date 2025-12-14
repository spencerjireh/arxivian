"""Agentic RAG router with LangGraph."""

from fastapi import APIRouter
from time import time

from src.schemas.ask_agentic import AgenticAskRequest, AgenticAskResponse
from src.schemas.common import SourceInfo
from src.dependencies import DbSession
from src.services.factories.service_factories import get_agentic_rag_service

router = APIRouter()


@router.post("/ask-agentic", response_model=AgenticAskResponse)
async def ask_agentic(request: AgenticAskRequest, db: DbSession) -> AgenticAskResponse:
    """
    Agentic RAG with LangGraph workflow.

    Features:
    - Guardrail validation (rejects out-of-scope queries)
    - Document grading (filters irrelevant chunks)
    - Query rewriting (improves retrieval iteratively)
    - Transparent reasoning steps

    Process:
    1. Guardrail: Validate query is about AI/ML research
    2. Retrieve: Hybrid search for chunks
    3. Grade: LLM grades each chunk for relevance
    4. Rewrite: If not enough relevant chunks, rewrite query and retry
    5. Generate: Create answer from relevant chunks

    Args:
        request: Question and parameters
        db: Database session

    Returns:
        AgenticAskResponse with answer, sources, and reasoning
    """
    start_time = time()

    # Create service with request parameters
    agentic_service = get_agentic_rag_service(
        db_session=db,
        model_name=request.model,
        guardrail_threshold=request.guardrail_threshold,
        top_k=request.top_k,
        max_retrieval_attempts=request.max_retrieval_attempts,
    )

    # Execute workflow
    result = await agentic_service.ask(request.query)

    # Convert sources to schema
    sources = [SourceInfo(**source) for source in result["sources"]]

    execution_time = (time() - start_time) * 1000

    return AgenticAskResponse(
        query=result["query"],
        answer=result["answer"],
        sources=sources,
        reasoning_steps=result["reasoning_steps"],
        retrieval_attempts=result["retrieval_attempts"],
        rewritten_query=result.get("rewritten_query"),
        guardrail_score=result["guardrail_score"],
        execution_time_ms=execution_time,
    )
