"""Database transaction middleware."""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.logger import logger


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
        # Process request
        try:
            response = await call_next(request)

            # Auto-commit on success (2xx status codes)
            # Note: DB session commit/rollback is handled via dependency injection
            # This middleware is here for future enhancements or explicit transaction control
            if 200 <= response.status_code < 300:
                # Get DB session from request state if available
                if hasattr(request.state, "db_session"):
                    db: AsyncSession = request.state.db_session
                    await db.commit()
                    logger.debug("Transaction committed")

            return response

        except Exception:
            # Auto-rollback on exceptions
            if hasattr(request.state, "db_session"):
                db: AsyncSession = request.state.db_session
                await db.rollback()
                logger.debug("Transaction rolled back due to exception")

            # Re-raise to be handled by exception handlers
            raise
