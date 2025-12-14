"""Health check schemas."""

from typing import Dict, Literal
from pydantic import BaseModel


class ServiceStatus(BaseModel):
    """Status of an individual service."""

    status: Literal["healthy", "unhealthy"]
    message: str
    details: Dict = {}


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["ok", "degraded"]
    version: str
    services: Dict[str, ServiceStatus]
    timestamp: str
