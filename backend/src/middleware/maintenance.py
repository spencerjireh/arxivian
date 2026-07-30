"""Maintenance-mode middleware.

When `settings.maintenance_mode` is on, every request returns 503 except a small
allowlist (health check + root), so the container stays healthy while the app is curtained
off during the pivot. Toggled by the `MAINTENANCE_MODE` env var; no code change or redeploy
of the image is needed to flip it.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from src.config import get_settings

# Paths that must keep working while curtained: the health check (so orchestration does not
# mark the container unhealthy) and the root ping.
_ALLOWED_PATHS: frozenset[str] = frozenset({"/", "/api/v1/health"})

# Retry-After hint (seconds) for clients; advisory only.
_RETRY_AFTER = "3600"


async def maintenance_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Short-circuit non-allowlisted requests with 503 when maintenance mode is on."""
    if get_settings().maintenance_mode and request.url.path not in _ALLOWED_PATHS:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers={"Retry-After": _RETRY_AFTER},
            content={
                "maintenance": True,
                "message": "Arxivian is being rebuilt. The service is temporarily unavailable.",
            },
        )
    return await call_next(request)
