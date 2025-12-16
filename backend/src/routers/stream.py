"""Streaming router with Server-Sent Events (SSE)."""

import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.schemas.stream import StreamRequest, StreamEventType, ErrorEventData, StreamEvent
from src.dependencies import DbSession
from src.factories.service_factories import get_agent_service
from src.utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)


@router.post("/stream")
async def stream(request: StreamRequest, db: DbSession) -> StreamingResponse:
    """
    Stream agent response via Server-Sent Events (SSE).

    This endpoint streams the agent's response in real-time, providing
    status updates, content tokens, and metadata as separate events.

    Features:
    - Multi-provider LLM support (OpenAI, Z.AI)
    - Guardrail validation (rejects out-of-scope queries)
    - Document grading (filters irrelevant chunks)
    - Query rewriting (improves retrieval iteratively)
    - Streaming answer generation
    - Multi-turn conversation memory (optional)

    SSE Event Types:
    - status: Workflow step updates (guardrail, retrieval, grading, generation)
    - content: Streaming answer tokens
    - sources: Retrieved document sources
    - metadata: Final execution metadata
    - error: Error information (if any)
    - done: Stream complete

    Args:
        request: Question and parameters (including optional provider/model and session_id)
        db: Database session

    Returns:
        StreamingResponse with SSE events
    """
    log.info(
        "stream request",
        query=request.query[:100],
        provider=request.provider,
        session_id=request.session_id,
    )

    async def event_generator():
        try:
            # Create service with request parameters
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

            # Stream events from the agent service
            async for event in agent_service.ask_stream(
                request.query, session_id=request.session_id
            ):
                # Format as SSE
                event_type = event.event.value
                if hasattr(event.data, "model_dump"):
                    data_json = json.dumps(event.data.model_dump())
                else:
                    data_json = json.dumps(event.data)

                yield f"event: {event_type}\ndata: {data_json}\n\n"

        except Exception as e:
            log.error("stream error", error=str(e), exc_info=True)
            error_event = StreamEvent(
                event=StreamEventType.ERROR,
                data=ErrorEventData(error=str(e)),
            )
            yield f"event: error\ndata: {json.dumps(error_event.data.model_dump())}\n\n"
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
