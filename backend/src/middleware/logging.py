"""Request logging middleware with body capture."""

import time
import uuid
from typing import Callable, Awaitable

from fastapi import Request, Response
from starlette.responses import StreamingResponse
from starlette.types import ASGIApp

from src.config import get_settings
from src.utils.logger import get_logger, set_request_id, clear_request_id, truncate

log = get_logger(__name__)
settings = get_settings()

# Paths to skip logging (noisy/health endpoints)
SKIP_PATHS = {"/health", "/api/v1/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}
SLOW_REQUEST_MS = 2000


async def logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Middleware for request/response logging with timing and body capture.

    Works with StreamingResponse by logging before and after the stream starts.
    """
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
        "request_id": request_id,
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

            if request_body:
                req_data["body"] = truncate(request_body.decode("utf-8", errors="replace"))

        except Exception as e:
            log.error("failed to capture request body", error=str(e), error_type=type(e).__name__)

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
            "request_id": request_id,
        }

        # For streaming responses, log without reading the body
        # (body will be consumed by the client as it streams)
        # Check for StreamingResponse (including _StreamingResponse wrapper from middleware)
        # or text/event-stream media type, or if it has body_iterator attribute
        is_streaming = (
            isinstance(response, StreamingResponse)
            or "StreamingResponse" in type(response).__name__
            or (hasattr(response, "media_type") and response.media_type == "text/event-stream")
        )

        if is_streaming:
            resp_data["streaming"] = True
        elif settings.log_response_body:
            # Only capture body for non-streaming responses
            try:
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                if response_body:
                    resp_data["body"] = truncate(response_body.decode("utf-8", errors="replace"))
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
            request_id=request_id,
        )
        raise

    finally:
        clear_request_id()
