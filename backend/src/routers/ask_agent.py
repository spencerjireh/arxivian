"""Agent router with LangGraph."""

from fastapi import APIRouter, HTTPException
from time import time

from src.schemas.ask_agent import AgentAskRequest, AgentAskResponse
from src.schemas.common import SourceInfo
from src.dependencies import DbSession
from src.factories.service_factories import get_agent_service

router = APIRouter()


@router.post("/ask-agent", response_model=AgentAskResponse)
async def ask_agent(request: AgentAskRequest, db: DbSession) -> AgentAskResponse:
    """
    YSE Agent with LangGraph workflow.

    Features:
    - Multi-provider LLM support (OpenAI, Z.AI)
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
        request: Question and parameters (including optional provider/model)
        db: Database session

    Returns:
        AgentAskResponse with answer, sources, and reasoning
    """
    start_time = time()

    try:
        # Create service with request parameters
        # get_agent_service will validate provider/model
        agent_service = get_agent_service(
            db_session=db,
            provider=request.provider,
            model=request.model,
            guardrail_threshold=request.guardrail_threshold,
            top_k=request.top_k,
            max_retrieval_attempts=request.max_retrieval_attempts,
            temperature=request.temperature,
        )

        # Execute workflow
        result = await agent_service.ask(request.query)

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
        )

    except ValueError as e:
        # Handle validation errors (invalid provider/model)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle other errors
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
