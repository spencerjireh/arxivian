"""Streaming router with Server-Sent Events (SSE)."""

import asyncio
import json
import uuid
from uuid import UUID

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
    RedisDep,
    ConversationRepoDep,
    PaperRepoDep,
)
from src.exceptions import (
    BaseAPIException,
    ConflictError,
    PaperNotIngestedError,
    ScopeMismatchError,
)
from src.factories.service_factories import get_agent_service
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.paper_repository import PaperRepository
from src.services.agent_service.context import ScopedPaper
from src.services.task_registry import task_registry
from src.utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)


def _format_sse_error(error: str, code: str) -> str:
    """Format an error as an SSE event."""
    error_data = ErrorEventData(error=error, code=code)
    return f"event: error\ndata: {json.dumps(error_data.model_dump())}\n\n"


_USER_SAFE_ERROR_CODES: frozenset[str] = frozenset(
    {
        "USAGE_LIMIT_EXCEEDED",
        "CHECKPOINT_EXPIRED",
        "FORBIDDEN",
        "CONFLICT",
        "PAPER_NOT_INGESTED",
        "SCOPE_MISMATCH",
    }
)


async def resolve_scoped_paper(
    request: StreamRequest,
    session_id: str | None,
    user_id: UUID,
    conversation_repo: ConversationRepository,
    paper_repo: PaperRepository,
) -> ScopedPaper | None:
    """Work out the paper scope for this stream (SPE-277).

    A persisted scope (the conversation's `paper_id`) wins, so follow-ups and resumes stay
    narrowed without the client re-sending `arxiv_id`. A request that names a different
    paper than the conversation is scoped to is a 409 rather than a silent re-scope.
    """
    persisted_paper_id: UUID | None = None
    if session_id:
        conv = await conversation_repo.get_by_session_id(session_id, user_id=user_id)
        if conv is not None and isinstance(conv.paper_id, UUID):
            persisted_paper_id = conv.paper_id

    if request.arxiv_id is None and persisted_paper_id is None:
        return None

    if request.arxiv_id is not None:
        paper = await paper_repo.get_by_arxiv_id(request.arxiv_id)
        if paper is None or not paper.pdf_processed:
            raise PaperNotIngestedError(request.arxiv_id)
        if persisted_paper_id is not None and persisted_paper_id != paper.id:
            raise ScopeMismatchError(session_id or "", request.arxiv_id)
    else:
        paper = await paper_repo.get_by_id(str(persisted_paper_id))
        if paper is None or not paper.pdf_processed:
            raise PaperNotIngestedError(str(persisted_paper_id))

    return ScopedPaper(paper_id=str(paper.id), arxiv_id=paper.arxiv_id, title=paper.title)


@router.post("/stream")
async def stream(
    request: StreamRequest,
    db: DbSession,
    http_request: Request,
    current_user: CurrentUserRequired,
    policy: TierPolicyDep,
    usage_repo: UsageCounterRepoDep,
    conversation_repo: ConversationRepoDep,
    paper_repo: PaperRepoDep,
    graph: AgentGraphDep,
    redis: RedisDep,
    _limit: ChatGuard,
    _settings: SettingsGuard,
) -> StreamingResponse:
    """
    Stream agent response via Server-Sent Events (SSE).

    Supports two modes:
    - query: start a new agent interaction
    - resume: continue a paused HITL confirmation flow

    Requires authentication.
    """
    settings = get_settings()
    is_resume = request.resume is not None

    # For resume requests, read stored model/temperature from the pending turn
    if is_resume:
        pending_turn = await conversation_repo.get_pending_turn(
            request.resume.session_id, current_user.id
        )
        if not pending_turn or not pending_turn.pending_confirmation:
            raise ConflictError("No pending confirmation for this session")
        pending = pending_turn.pending_confirmation
        model = policy.resolve_model(pending.get("model"), settings)
        temperature = pending.get("temperature", 0.3)
    else:
        model = policy.resolve_model(request.model, settings)
        temperature = request.temperature

    # Determine timeout: request override > server default
    timeout_seconds = (
        request.timeout_seconds
        if request.timeout_seconds is not None
        else settings.agent_timeout_seconds
    )

    # Use session_id if provided, otherwise generate a temporary task ID
    task_id = (request.resume.session_id if is_resume else request.session_id) or str(uuid.uuid4())

    user_id = current_user.id

    scoped_paper = await resolve_scoped_paper(
        request,
        request.resume.session_id if is_resume else request.session_id,
        user_id,
        conversation_repo,
        paper_repo,
    )

    log.info(
        "stream request",
        query=request.query[:100] if request.query else "[resume]",
        model=model,
        session_id=request.session_id if not is_resume else request.resume.session_id,
        task_id=task_id,
        timeout_seconds=timeout_seconds,
        max_iterations=request.max_iterations,
        user_id=str(user_id),
        tier=current_user.tier,
        is_resume=is_resume,
        scoped_arxiv_id=scoped_paper.arxiv_id if scoped_paper else None,
    )

    async def event_generator():
        # Only increment usage counter for new queries (not resumes)
        if not is_resume:
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
                    temperature=temperature,
                    session_id=request.session_id if not is_resume else request.resume.session_id,
                    conversation_window=request.conversation_window,
                    max_iterations=request.max_iterations,
                    user_id=user_id,
                    can_ingest=policy.can_ingest,
                    can_search_arxiv=policy.can_search_arxiv,
                    graph=graph,
                    redis=redis,
                    daily_ingests=policy.daily_ingests,
                    usage_counter_repo=usage_repo,
                    scoped_paper=scoped_paper,
                )

                # Route to ask_stream or resume_stream
                if is_resume:
                    event_stream = agent_service.resume_stream(
                        session_id=request.resume.session_id,
                        thread_id=request.resume.thread_id,
                        approved=request.resume.approved,
                        selected_ids=request.resume.selected_ids,
                    )
                else:
                    event_stream = agent_service.ask_stream(
                        request.query, session_id=request.session_id
                    )

                async for event in event_stream:
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
            if isinstance(e, BaseAPIException) and e.error_code in _USER_SAFE_ERROR_CODES:
                yield _format_sse_error(e.message, e.error_code)
            else:
                yield _format_sse_error("An unexpected error occurred", "INTERNAL_ERROR")
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
