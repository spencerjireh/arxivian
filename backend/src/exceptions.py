"""Custom exception hierarchy for the application.

One class per HTTP status the API raises, plus the external-service errors that callers
branch on (rate limits carry `retry_after`). Every exception carries a stable `error_code`
that the error handler returns and the frontend may switch on.
"""

from typing import Any, Optional


class BaseAPIException(Exception):
    """Base exception for all API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


# --- 400 / 422 ---------------------------------------------------------------


class ValidationError(BaseAPIException):
    """Client input did not validate."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        error_code: str = "VALIDATION_ERROR",
    ):
        super().__init__(message, status_code=400, error_code=error_code, details=details)


class InvalidParameterError(ValidationError):
    """A parameter value is out of range or malformed."""

    def __init__(self, parameter: str, value: Any, reason: str):
        super().__init__(
            f"Invalid value for parameter '{parameter}': {reason}",
            details={"parameter": parameter, "value": value, "reason": reason},
            error_code="INVALID_PARAMETER",
        )


class InsufficientChunksError(BaseAPIException):
    """Document processing yielded too few chunks to index."""

    def __init__(self, arxiv_id: str, chunks_count: int, min_required: int = 1):
        super().__init__(
            f"Insufficient chunks generated for paper {arxiv_id}",
            status_code=422,
            error_code="INSUFFICIENT_CHUNKS",
            details={
                "arxiv_id": arxiv_id,
                "chunks_count": chunks_count,
                "min_required": min_required,
            },
        )


# --- 401 / 403 / 404 / 409 / 429 ---------------------------------------------


class AuthenticationError(BaseAPIException):
    """Request is not authenticated."""

    def __init__(self, message: str, error_code: str = "AUTHENTICATION_ERROR"):
        super().__init__(message, status_code=401, error_code=error_code)


class InvalidTokenError(AuthenticationError):
    def __init__(self, reason: str = "Token is invalid or expired"):
        super().__init__(reason, error_code="INVALID_TOKEN")


class MissingTokenError(AuthenticationError):
    def __init__(self):
        super().__init__("Authentication required", error_code="MISSING_TOKEN")


class InvalidApiKeyError(AuthenticationError):
    def __init__(self):
        super().__init__("Invalid or missing API key", error_code="INVALID_API_KEY")


class ForbiddenError(BaseAPIException):
    """The caller's tier or ownership does not allow the action."""

    def __init__(self, message: str):
        super().__init__(message, status_code=403, error_code="FORBIDDEN")


class ResourceNotFoundError(BaseAPIException):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} not found",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class ConflictError(BaseAPIException):
    def __init__(
        self,
        message: str,
        error_code: str = "CONFLICT",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, status_code=409, error_code=error_code, details=details)


class PaperNotIngestedError(ConflictError):
    """A paper-scoped chat targets a paper with no ingested full text."""

    def __init__(self, arxiv_id: str):
        super().__init__(
            f"Paper {arxiv_id} is not ingested yet",
            error_code="PAPER_NOT_INGESTED",
            details={"arxiv_id": arxiv_id},
        )


class ScopeMismatchError(ConflictError):
    """A request names a different paper than the conversation is scoped to."""

    def __init__(self, session_id: str, arxiv_id: str):
        super().__init__(
            f"Conversation {session_id} is scoped to a different paper",
            error_code="SCOPE_MISMATCH",
            details={"session_id": session_id, "arxiv_id": arxiv_id},
        )


class UsageLimitExceededError(BaseAPIException):
    def __init__(self, current: int, limit: int):
        super().__init__(
            f"Daily limit reached ({current}/{limit}). Resets at midnight UTC.",
            status_code=429,
            error_code="USAGE_LIMIT_EXCEEDED",
            details={"current": current, "limit": limit},
        )


# --- 500 / 502 / 504 ----------------------------------------------------------


class DatabaseError(BaseAPIException):
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR", details=details)


class ExternalServiceError(BaseAPIException):
    """An upstream service failed. `details["service"]` names it."""

    def __init__(
        self,
        service_name: str,
        message: str,
        status_code: int = 502,
        error_code: str = "EXTERNAL_SERVICE_ERROR",
        details: Optional[dict[str, Any]] = None,
    ):
        details = {**(details or {}), "service": service_name}
        super().__init__(message, status_code=status_code, error_code=error_code, details=details)


class _RateLimited:
    """Mixin: records `retry_after` (seconds) on a rate-limit error."""

    retry_after: Optional[float]

    @staticmethod
    def _with_retry(details: Optional[dict[str, Any]], retry_after: Optional[float]) -> dict:
        details = dict(details or {})
        if retry_after is not None:
            details["retry_after"] = retry_after
        return details


class ArxivAPIError(ExternalServiceError):
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__("arXiv", message, error_code="ARXIV_API_ERROR", details=details)


class EmbeddingServiceError(ExternalServiceError):
    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        error_code: str = "EMBEDDING_SERVICE_ERROR",
    ):
        super().__init__("Jina Embeddings", message, error_code=error_code, details=details)


class EmbeddingRateLimitError(EmbeddingServiceError, _RateLimited):
    def __init__(
        self,
        message: str = "Embedding API rate limit exceeded",
        retry_after: Optional[float] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message, self._with_retry(details, retry_after), error_code="EMBEDDING_RATE_LIMIT"
        )
        self.retry_after = retry_after


class SemanticScholarError(ExternalServiceError):
    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        error_code: str = "SEMANTIC_SCHOLAR_ERROR",
    ):
        super().__init__("Semantic Scholar", message, error_code=error_code, details=details)


class SemanticScholarRateLimitError(SemanticScholarError, _RateLimited):
    def __init__(
        self,
        message: str = "Semantic Scholar API rate limit exceeded",
        retry_after: Optional[float] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            self._with_retry(details, retry_after),
            error_code="SEMANTIC_SCHOLAR_RATE_LIMIT",
        )
        self.retry_after = retry_after


class TypeSafeError(ExternalServiceError):
    """The TypeSafe (Jev) API returned an error.

    Carries the upstream HTTP status and request id so a failed scoring judgment can be
    traced in the TypeSafe console. Non-retryable by default (4xx other than 429).
    """

    def __init__(
        self,
        message: str,
        status: Optional[int] = None,
        request_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        error_code: str = "TYPESAFE_ERROR",
    ):
        details = dict(details or {})
        if status is not None:
            details["typesafe_status"] = status
        if request_id is not None:
            details["request_id"] = request_id
        super().__init__("TypeSafe", message, error_code=error_code, details=details)
        self.status = status
        self.request_id = request_id


class TypeSafeRateLimitError(TypeSafeError, _RateLimited):
    """TypeSafe returned 429. `retry_after` is in seconds (may be absent)."""

    def __init__(
        self,
        message: str = "TypeSafe API rate limit exceeded",
        retry_after: Optional[float] = None,
        request_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status=429,
            request_id=request_id,
            details=self._with_retry(details, retry_after),
            error_code="TYPESAFE_RATE_LIMIT",
        )
        self.retry_after = retry_after


class TypeSafeConnectionError(TypeSafeError):
    """TypeSafe cannot be reached or timed out (after SDK retries); the scoring task retries."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, details=details, error_code="TYPESAFE_CONNECTION_ERROR")


class PDFProcessingError(ExternalServiceError):
    def __init__(self, arxiv_id: str, stage: str, message: str):
        super().__init__(
            "PDF Processing",
            f"PDF processing failed at {stage}: {message}",
            error_code="PDF_PROCESSING_ERROR",
            details={"arxiv_id": arxiv_id, "stage": stage, "underlying_error": message},
        )


class LLMTimeoutError(ExternalServiceError):
    def __init__(self, provider: str, timeout_seconds: float):
        super().__init__(
            f"LLM-{provider}",
            f"LLM call to {provider} timed out after {timeout_seconds}s",
            status_code=504,
            error_code="LLM_TIMEOUT",
            details={"provider": provider, "timeout_seconds": timeout_seconds},
        )


class ScoringError(Exception):
    """The Stage 2 scoring graph cannot score a paper.

    Not HTTP-facing (scoring runs in a Celery task). Raising this from a node aborts the
    graph invocation so Celery's autoretry re-runs the paper -- used for hard failures like
    'no usable full text', where partial scoring is not meaningful.
    """
