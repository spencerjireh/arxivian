"""Health check schemas."""

from typing import Literal

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    """Status of an individual service."""

    status: Literal["healthy", "unhealthy"]
    message: str
    details: dict = {}


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["ok", "degraded"]
    version: str
    services: dict[str, ServiceStatus]
    timestamp: str
