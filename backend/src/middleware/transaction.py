"""Database transaction middleware."""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.logger import get_logger

log = get_logger(__name__)


class TransactionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic database transaction management.

    Commits on successful responses (2xx), rolls back on exceptions.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with transaction management.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        try:
            response = await call_next(request)

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
