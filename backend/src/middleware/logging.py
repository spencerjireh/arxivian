"""Request logging middleware."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import clear_request_id, logger, set_request_id


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with logging.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        # Generate request ID
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        set_request_id(request_id)

        # Add request_id to request state for access in handlers
        request.state.request_id = request_id

        # Log request start
        start_time = time.time()
        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client": request.client.host if request.client else None,
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"← {request.method} {request.url.path} - {response.status_code} ({duration_ms:.2f}ms)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            # Add request_id to response headers for debugging
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Log exception (will be handled by exception handlers)
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"✗ {request.method} {request.url.path} - Exception ({duration_ms:.2f}ms)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "exception": str(exc),
                },
                exc_info=True,
            )
            raise

        finally:
            # Clean up context
            clear_request_id()
