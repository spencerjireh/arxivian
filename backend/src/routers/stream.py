"""Streaming router with Server-Sent Events (SSE)."""

import asyncio
import json
import uuid
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.dependencies import (
    AgentGraphDep,
    ChatGuard,
    ConversationRepoDep,
    CurrentUserRequired,
    DbSession,
    PaperRepoDep,
    SettingsDep,
    UsageCounterRepoDep,
)
from src.exceptions import BaseAPIException, PaperNotIngestedError, ScopeMismatchError
from src.factories import get_agent_service
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.paper_repository import PaperRepository
from src.schemas.stream import ErrorEventData, StreamEvent, StreamRequest
from src.services.agent_service.context import ScopedPaper
from src.utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)


class EventStreamResponse(StreamingResponse):
    """StreamingResponse whose media type puts the 200 under text/event-stream in OpenAPI."""

    media_type = "text/event-stream"


def _format_sse_error(error: str, code: str) -> str:
    """Format an error as an SSE event."""
    error_data = ErrorEventData(error=error, code=code)
    return f"event: error\ndata: {json.dumps(error_data.model_dump())}\n\n"


_USER_SAFE_ERROR_CODES: frozenset[str] = frozenset(
    {"USAGE_LIMIT_EXCEEDED", "FORBIDDEN", "CONFLICT", "PAPER_NOT_INGESTED", "SCOPE_MISMATCH"}
)


async def resolve_scoped_paper(
    request: StreamRequest,
    user_id: UUID,
    conversation_repo: ConversationRepository,
    paper_repo: PaperRepository,
) -> ScopedPaper:
    """Work out the paper scope for this stream (SPE-277).

    A persisted scope (the conversation's `paper_id`) wins, so follow-ups stay narrowed to
    the paper the thread started on. A request that names a different paper than the
    conversation is scoped to is a 409 rather than a silent re-scope.
    """
    paper = await paper_repo.get_by_arxiv_id(request.arxiv_id)
    if paper is None or not paper.pdf_processed:
        raise PaperNotIngestedError(request.arxiv_id)

    if request.session_id:
        conv = await conversation_repo.get_by_session_id(request.session_id, user_id=user_id)
        if conv is not None and isinstance(conv.paper_id, UUID) and conv.paper_id != paper.id:
            raise ScopeMismatchError(request.session_id, request.arxiv_id)

    return ScopedPaper(paper_id=str(paper.id), arxiv_id=paper.arxiv_id, title=paper.title)


@router.post(
    "/stream",
    response_class=EventStreamResponse,
    # Registers StreamEvent and its data members in the document; the frontend's generated
    # types come from there. Each SSE `data` line is one StreamEvent.data member.
    responses={200: {"model": StreamEvent, "description": "Server-sent events"}},
)
async def stream(
    request: StreamRequest,
    db: DbSession,
    http_request: Request,
    current_user: CurrentUserRequired,
    usage_repo: UsageCounterRepoDep,
    conversation_repo: ConversationRepoDep,
    paper_repo: PaperRepoDep,
    graph: AgentGraphDep,
    settings: SettingsDep,
    _limit: ChatGuard,
) -> StreamingResponse:
    """Stream one turn of a paper-scoped conversation via Server-Sent Events."""
    timeout_seconds = settings.agent_timeout_seconds
    task_id = request.session_id or str(uuid.uuid4())
    user_id = current_user.id

    scoped_paper = await resolve_scoped_paper(request, user_id, conversation_repo, paper_repo)

    log.info(
        "stream request",
        query=request.query[:100],
        session_id=request.session_id,
        task_id=task_id,
        user_id=str(user_id),
        tier=current_user.tier,
        scoped_arxiv_id=scoped_paper.arxiv_id,
    )

    async def event_generator():
        await usage_repo.increment_query_count(current_user.id)
        await db.flush()

        try:
            async with asyncio.timeout(timeout_seconds):
                agent_service = get_agent_service(
                    db_session=db,
                    user_id=user_id,
                    graph=graph,
                    scoped_paper=scoped_paper,
                )

                async for event in agent_service.ask_stream(
                    request.query, session_id=request.session_id
                ):
                    if await http_request.is_disconnected():
                        log.info("client disconnected", task_id=task_id)
                        break

                    event_type = event.event.value
                    if isinstance(event.data, BaseModel):
                        data_json = json.dumps(event.data.model_dump())
                    else:
                        data_json = json.dumps(event.data)

                    yield f"event: {event_type}\ndata: {data_json}\n\n"

        except TimeoutError:
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

    return EventStreamResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
