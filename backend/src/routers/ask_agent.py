"""Agent router with LangGraph."""

from fastapi import APIRouter
from time import time

from src.schemas.ask_agent import AgentAskRequest, AgentAskResponse
from src.schemas.common import SourceInfo
from src.dependencies import DbSession
from src.factories.service_factories import get_agent_service

router = APIRouter()


@router.post("/ask-agent", response_model=AgentAskResponse)
async def ask_agent(request: AgentAskRequest, db: DbSession) -> AgentAskResponse:
    """
    Jireh's Agent with LangGraph workflow.

    Features:
    - Multi-provider LLM support (OpenAI, Z.AI)
    - Guardrail validation (rejects out-of-scope queries)
    - Document grading (filters irrelevant chunks)
    - Query rewriting (improves retrieval iteratively)
    - Transparent reasoning steps
    - Multi-turn conversation memory (optional)

    Process:
    1. Guardrail: Validate query is about AI/ML research
    2. Retrieve: Hybrid search for chunks
    3. Grade: LLM grades each chunk for relevance
    4. Rewrite: If not enough relevant chunks, rewrite query and retry
    5. Generate: Create answer from relevant chunks

    Args:
        request: Question and parameters (including optional provider/model and session_id)
        db: Database session

    Returns:
        AgentAskResponse with answer, sources, reasoning, and session info
    """
    start_time = time()

    # Create service with request parameters
    # get_agent_service will validate provider/model and raise exceptions if invalid
    agent_service = get_agent_service(
        db_session=db,
        provider=request.provider,
        model=request.model,
        guardrail_threshold=request.guardrail_threshold,
        top_k=request.top_k,
        max_retrieval_attempts=request.max_retrieval_attempts,
        temperature=request.temperature,
        session_id=request.session_id,
        conversation_window=request.conversation_window,
    )

    # Execute workflow with session_id for conversation continuity
    result = await agent_service.ask(request.query, session_id=request.session_id)

    # Convert sources to schema
    sources = [SourceInfo(**source) for source in result["sources"]]

    execution_time = (time() - start_time) * 1000

    return AgentAskResponse(
        query=result["query"],
        answer=result["answer"],
        sources=sources,
        reasoning_steps=result["reasoning_steps"],
        retrieval_attempts=result["retrieval_attempts"],
        rewritten_query=result.get("rewritten_query"),
        guardrail_score=result["guardrail_score"],
        provider=result["provider"],
        model=result["model"],
        execution_time_ms=execution_time,
        session_id=result.get("session_id"),
        turn_number=result.get("turn_number", 0),
    )
