"""Streaming router with Server-Sent Events (SSE)."""

import asyncio
import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config import get_settings
from src.schemas.stream import StreamRequest, ErrorEventData
from src.dependencies import (
    DbSession,
    CurrentUserRequired,
    TierPolicyDep,
    ChatGuard,
    SettingsGuard,
    UsageCounterRepoDep,
    AgentGraphDep,
)
from src.factories.service_factories import get_agent_service
from src.services.task_registry import task_registry
from src.utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)


def _format_sse_error(error: str, code: str) -> str:
    """Format an error as an SSE event."""
    error_data = ErrorEventData(error=error, code=code)
    return f"event: error\ndata: {json.dumps(error_data.model_dump())}\n\n"


@router.post("/stream")
async def stream(
    request: StreamRequest,
    db: DbSession,
    http_request: Request,
    current_user: CurrentUserRequired,
    policy: TierPolicyDep,
    usage_repo: UsageCounterRepoDep,
    graph: AgentGraphDep,
    _limit: ChatGuard,
    _settings: SettingsGuard,
) -> StreamingResponse:
    """
    Stream agent response via Server-Sent Events (SSE).

    Supports free (all tools, DB rate limit) and pro (unlimited) tiers.
    Requires authentication.
    """
    settings = get_settings()

    # Resolve model based on tier policy
    model = policy.resolve_model(request.model, settings)

    # Determine timeout: request override > server default
    timeout_seconds = (
        request.timeout_seconds
        if request.timeout_seconds is not None
        else settings.agent_timeout_seconds
    )

    # Use session_id if provided, otherwise generate a temporary task ID
    task_id = request.session_id or str(uuid.uuid4())

    user_id = current_user.id

    log.info(
        "stream request",
        query=request.query[:100],
        model=model,
        session_id=request.session_id,
        task_id=task_id,
        timeout_seconds=timeout_seconds,
        max_iterations=request.max_iterations,
        user_id=str(user_id),
        tier=current_user.tier,
    )

    async def event_generator():
        # Increment usage counter
        await usage_repo.increment_query_count(current_user.id)
        await db.flush()

        # Register the current task for cancellation support
        current_task = asyncio.current_task()
        if current_task is not None:
            task_registry.register(task_id, current_task, user_id=str(user_id))

        try:
            async with asyncio.timeout(timeout_seconds):
                # Create service with request parameters and tier-based tool gating
                agent_service = get_agent_service(
                    db_session=db,
                    model=model,
                    guardrail_threshold=request.guardrail_threshold,
                    top_k=request.top_k,
                    max_retrieval_attempts=request.max_retrieval_attempts,
                    temperature=request.temperature,
                    session_id=request.session_id,
                    conversation_window=request.conversation_window,
                    max_iterations=request.max_iterations,
                    user_id=user_id,
                    can_ingest=policy.can_ingest,
                    can_search_arxiv=policy.can_search_arxiv,
                    graph=graph,
                    daily_ingests=policy.daily_ingests,
                    usage_counter_repo=usage_repo,
                )

                # Stream events from the agent service
                async for event in agent_service.ask_stream(
                    request.query, session_id=request.session_id
                ):
                    # Check if client disconnected
                    if await http_request.is_disconnected():
                        log.info("client disconnected", task_id=task_id)
                        break

                    # Format as SSE
                    event_type = event.event.value
                    if isinstance(event.data, BaseModel):
                        data_json = json.dumps(event.data.model_dump())
                    else:
                        data_json = json.dumps(event.data)

                    yield f"event: {event_type}\ndata: {data_json}\n\n"

        except asyncio.TimeoutError:
            log.warning("stream timeout", task_id=task_id, timeout_seconds=timeout_seconds)
            yield _format_sse_error(f"Request timed out after {timeout_seconds} seconds", "TIMEOUT")
            yield "event: done\ndata: {}\n\n"

        except asyncio.CancelledError:
            log.info("stream cancelled", task_id=task_id)
            yield _format_sse_error("Stream cancelled", "CANCELLED")
            yield "event: done\ndata: {}\n\n"

        except Exception as e:
            log.error("stream error", error=str(e), task_id=task_id, exc_info=True)
            yield _format_sse_error(str(e), "INTERNAL_ERROR")
            yield "event: done\ndata: {}\n\n"

        finally:
            # Always unregister the task when done
            task_registry.unregister(task_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
