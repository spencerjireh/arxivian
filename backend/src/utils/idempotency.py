"""Idempotency token management for preventing duplicate request processing."""

import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from src.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class IdempotencyEntry:
    """Entry for tracking an in-flight or completed request."""

    key: str
    status: str  # "in_progress", "completed", "failed"
    response: Optional[Any] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class IdempotencyStore:
    """
    In-memory idempotency token store.

    Prevents duplicate processing of requests by tracking in-flight and
    recently completed requests. Clients can include an idempotency_key
    with their request to ensure the same operation is not performed twice.

    For multi-instance deployments, replace with Redis implementation.
    """

    def __init__(self, ttl_minutes: int = 30):
        """
        Initialize idempotency store.

        Args:
            ttl_minutes: Time-to-live for entries in minutes
        """
        self._store: Dict[str, IdempotencyEntry] = {}
        self._lock = asyncio.Lock()
        self._ttl = timedelta(minutes=ttl_minutes)

    async def acquire(self, key: str) -> Optional[IdempotencyEntry]:
        """
        Try to acquire lock for an idempotency key.

        Args:
            key: Unique idempotency key from client

        Returns:
            None if key was acquired (proceed with request)
            IdempotencyEntry if key already exists (return cached response or wait)
        """
        async with self._lock:
            self._cleanup_expired()

            if key in self._store:
                entry = self._store[key]
                log.debug("idempotency key exists", key=key, status=entry.status)
                return entry

            # Acquire the key
            self._store[key] = IdempotencyEntry(key=key, status="in_progress")
            log.debug("idempotency key acquired", key=key)
            return None

    async def complete(self, key: str, response: Any) -> None:
        """
        Mark request as completed with response.

        Args:
            key: Idempotency key
            response: Response to cache for duplicate requests
        """
        async with self._lock:
            if key in self._store:
                self._store[key].status = "completed"
                self._store[key].response = response
                log.debug("idempotency key completed", key=key)

    async def fail(self, key: str) -> None:
        """
        Mark request as failed and release the key.

        Failed requests should be retryable, so we remove the key entirely.

        Args:
            key: Idempotency key
        """
        async with self._lock:
            if key in self._store:
                del self._store[key]
                log.debug("idempotency key released after failure", key=key)

    def _cleanup_expired(self) -> None:
        """Remove expired entries. Must be called with lock held."""
        now = datetime.now(timezone.utc)
        expired = [k for k, v in self._store.items() if now - v.created_at > self._ttl]
        for k in expired:
            del self._store[k]
        if expired:
            log.debug("cleaned up expired idempotency keys", count=len(expired))


# Singleton instance
idempotency_store = IdempotencyStore()
