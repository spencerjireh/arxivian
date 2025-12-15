"""Custom exception hierarchy for the application."""

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
        """
        Initialize base exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            details: Additional context about the error
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# ============================================================================
# Validation Errors (400)
# ============================================================================


class ValidationError(BaseAPIException):
    """Base class for validation errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR", details=details)


class InvalidProviderError(ValidationError):
    """Raised when an invalid LLM provider is specified."""

    def __init__(self, provider: str, valid_providers: list[str]):
        super().__init__(
            message=f"Invalid provider '{provider}'",
            details={"provider": provider, "valid_providers": valid_providers},
        )
        self.error_code = "INVALID_PROVIDER"


class InvalidModelError(ValidationError):
    """Raised when an invalid model is specified for a provider."""

    def __init__(self, model: str, provider: str, valid_models: list[str]):
        super().__init__(
            message=f"Invalid model '{model}' for provider '{provider}'",
            details={"model": model, "provider": provider, "valid_models": valid_models},
        )
        self.error_code = "INVALID_MODEL"


class InvalidParameterError(ValidationError):
    """Raised when an invalid parameter value is provided."""

    def __init__(self, parameter: str, value: Any, reason: str):
        super().__init__(
            message=f"Invalid value for parameter '{parameter}': {reason}",
            details={"parameter": parameter, "value": value, "reason": reason},
        )
        self.error_code = "INVALID_PARAMETER"


# ============================================================================
# Not Found Errors (404)
# ============================================================================


class NotFoundError(BaseAPIException):
    """Base class for resource not found errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, status_code=404, error_code="NOT_FOUND", details=details)


class ResourceNotFoundError(NotFoundError):
    """Raised when a requested resource doesn't exist."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} not found",
            details={"resource_type": resource_type, "resource_id": resource_id},
        )
        self.error_code = "RESOURCE_NOT_FOUND"


# ============================================================================
# Business Logic Errors (422)
# ============================================================================


class BusinessLogicError(BaseAPIException):
    """Base class for business logic errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message, status_code=422, error_code="BUSINESS_LOGIC_ERROR", details=details
        )


class InsufficientChunksError(BusinessLogicError):
    """Raised when document processing yields insufficient chunks."""

    def __init__(self, arxiv_id: str, chunks_count: int, min_required: int = 1):
        super().__init__(
            message=f"Insufficient chunks generated for paper {arxiv_id}",
            details={
                "arxiv_id": arxiv_id,
                "chunks_count": chunks_count,
                "min_required": min_required,
            },
        )
        self.error_code = "INSUFFICIENT_CHUNKS"


class GuardrailRejectionError(BusinessLogicError):
    """Raised when a query is rejected by guardrail validation."""

    def __init__(self, query: str, score: float, threshold: float):
        super().__init__(
            message="Query rejected by guardrail - not related to AI/ML research",
            details={"query": query, "score": score, "threshold": threshold},
        )
        self.error_code = "GUARDRAIL_REJECTION"


class ProcessingLimitError(BusinessLogicError):
    """Raised when processing limits are exceeded."""

    def __init__(self, limit_type: str, current: int, maximum: int):
        super().__init__(
            message=f"Processing limit exceeded for {limit_type}",
            details={"limit_type": limit_type, "current": current, "maximum": maximum},
        )
        self.error_code = "PROCESSING_LIMIT_EXCEEDED"


# ============================================================================
# External Service Errors (502/503)
# ============================================================================


class ExternalServiceError(BaseAPIException):
    """Base class for external service errors."""

    def __init__(
        self,
        service_name: str,
        message: str,
        status_code: int = 502,
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        details["service"] = service_name
        super().__init__(
            message, status_code=status_code, error_code="EXTERNAL_SERVICE_ERROR", details=details
        )


class ArxivAPIError(ExternalServiceError):
    """Raised when arXiv API encounters an error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(service_name="arXiv", message=message, details=details)
        self.error_code = "ARXIV_API_ERROR"


class LLMProviderError(ExternalServiceError):
    """Raised when LLM provider encounters an error."""

    def __init__(self, provider: str, message: str, details: Optional[dict[str, Any]] = None):
        details = details or {}
        details["provider"] = provider
        super().__init__(service_name=f"LLM-{provider}", message=message, details=details)
        self.error_code = "LLM_PROVIDER_ERROR"


class EmbeddingServiceError(ExternalServiceError):
    """Raised when embedding service encounters an error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(service_name="Jina Embeddings", message=message, details=details)
        self.error_code = "EMBEDDING_SERVICE_ERROR"


class PDFProcessingError(ExternalServiceError):
    """Raised when PDF processing fails."""

    def __init__(self, arxiv_id: str, stage: str, message: str):
        super().__init__(
            service_name="PDF Processing",
            message=f"PDF processing failed at {stage}: {message}",
            details={"arxiv_id": arxiv_id, "stage": stage, "underlying_error": message},
        )
        self.error_code = "PDF_PROCESSING_ERROR"


# ============================================================================
# Database Errors (500)
# ============================================================================


class DatabaseError(BaseAPIException):
    """Base class for database errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR", details=details)


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(self, message: str):
        super().__init__(message=f"Database connection error: {message}")
        self.error_code = "DATABASE_CONNECTION_ERROR"


class TransactionError(DatabaseError):
    """Raised when database transaction fails."""

    def __init__(self, operation: str, message: str):
        super().__init__(
            message=f"Transaction error during {operation}: {message}",
            details={"operation": operation},
        )
        self.error_code = "TRANSACTION_ERROR"


# ============================================================================
# Configuration Errors (500)
# ============================================================================


class ConfigurationError(BaseAPIException):
    """Raised when application configuration is invalid."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message, status_code=500, error_code="CONFIGURATION_ERROR", details=details
        )
