"""Database transaction middleware."""

from typing import Callable, Awaitable

from fastapi import Request, Response
from starlette.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.logger import get_logger

log = get_logger(__name__)


async def transaction_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Middleware for automatic database transaction management.

    Commits on successful responses (2xx), rolls back on exceptions.
    For streaming responses, skips transaction management as they handle their own commits.
    """
    try:
        response = await call_next(request)

        # Skip transaction management for streaming responses
        # (they handle their own DB commits within the stream generator)
        if isinstance(response, StreamingResponse):
            log.debug("skipping transaction management for streaming response")
            return response

        # Auto-commit on success (2xx status codes)
        if 200 <= response.status_code < 300:
            if hasattr(request.state, "db_session"):
                db: AsyncSession = request.state.db_session
                await db.commit()
                log.debug("transaction committed")

        return response

    except Exception:
        # Auto-rollback on exceptions
        if hasattr(request.state, "db_session"):
            db: AsyncSession = request.state.db_session
            await db.rollback()
            log.debug("transaction rolled back")

        raise
