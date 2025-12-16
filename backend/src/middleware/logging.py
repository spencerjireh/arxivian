"""Request logging middleware with body capture."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from src.config import get_settings
from src.utils.logger import get_logger, set_request_id, clear_request_id, truncate

log = get_logger(__name__)
settings = get_settings()

# Paths to skip logging (noisy/health endpoints)
SKIP_PATHS = {"/health", "/api/v1/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}
SLOW_REQUEST_MS = 2000


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with timing and body capture."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip noisy endpoints
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        # Generate and set request ID
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        set_request_id(request_id)
        request.state.request_id = request_id

        start = time.perf_counter()
        method = request.method
        path = request.url.path

        # Build request log data
        req_data: dict = {
            "method": method,
            "path": path,
        }

        if request.client:
            req_data["client"] = request.client.host

        if request.query_params:
            req_data["query"] = dict(request.query_params)

        # Capture request body for mutations
        request_body: bytes | None = None
        if method in ("POST", "PUT", "PATCH") and settings.log_request_body:
            try:
                request_body = await request.body()

                # Re-create receive so downstream can read body
                async def receive():
                    return {"type": "http.request", "body": request_body}

                request._receive = receive

                if request_body:
                    req_data["body"] = truncate(request_body.decode("utf-8", errors="replace"))
            except Exception:
                pass

        log.info("request", **req_data)

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000

            # Build response log data
            resp_data: dict = {
                "method": method,
                "path": path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }

            # Capture response body if configured
            if settings.log_response_body and not isinstance(response, StreamingResponse):
                try:
                    # Read response body
                    response_body = b""
                    async for chunk in response.body_iterator:
                        response_body += chunk

                    if response_body:
                        resp_data["body"] = truncate(
                            response_body.decode("utf-8", errors="replace")
                        )
                        resp_data["body_size"] = len(response_body)

                    # Recreate response with body
                    response = Response(
                        content=response_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )
                except Exception:
                    pass

            # Log with appropriate level based on duration/status
            if response.status_code >= 500:
                log.error("response", **resp_data)
            elif response.status_code >= 400:
                log.warning("response", **resp_data)
            elif duration_ms > SLOW_REQUEST_MS:
                log.warning("response (slow)", **resp_data)
            else:
                log.info("response", **resp_data)

            # Add request ID header for client correlation
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            log.error(
                "request failed",
                method=method,
                path=path,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

        finally:
            clear_request_id()
