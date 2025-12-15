"""Quick test script for middleware and error handling."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.exceptions import (
    InvalidProviderError,
    InvalidModelError,
    PDFProcessingError,
    InsufficientChunksError,
    ConfigurationError,
)
from src.schemas.errors import ErrorResponse, ErrorDetail


def test_exceptions():
    """Test custom exceptions."""
    print("Testing custom exceptions...\n")

    # Test InvalidProviderError
    try:
        raise InvalidProviderError(provider="invalid", valid_providers=["openai", "zai"])
    except InvalidProviderError as e:
        print(f"✓ InvalidProviderError: {e.message}")
        print(f"  Status: {e.status_code}, Code: {e.error_code}")
        print(f"  Details: {e.details}\n")

    # Test InvalidModelError
    try:
        raise InvalidModelError(
            model="gpt-5", provider="openai", valid_models=["gpt-4o", "gpt-4o-mini"]
        )
    except InvalidModelError as e:
        print(f"✓ InvalidModelError: {e.message}")
        print(f"  Status: {e.status_code}, Code: {e.error_code}")
        print(f"  Details: {e.details}\n")

    # Test PDFProcessingError
    try:
        raise PDFProcessingError(arxiv_id="2301.12345", stage="download", message="HTTP 404")
    except PDFProcessingError as e:
        print(f"✓ PDFProcessingError: {e.message}")
        print(f"  Status: {e.status_code}, Code: {e.error_code}")
        print(f"  Details: {e.details}\n")

    # Test InsufficientChunksError
    try:
        raise InsufficientChunksError(arxiv_id="2301.12345", chunks_count=0)
    except InsufficientChunksError as e:
        print(f"✓ InsufficientChunksError: {e.message}")
        print(f"  Status: {e.status_code}, Code: {e.error_code}")
        print(f"  Details: {e.details}\n")

    # Test ConfigurationError
    try:
        raise ConfigurationError(
            message="API key not configured",
            details={"required_env_var": "OPENAI_API_KEY"},
        )
    except ConfigurationError as e:
        print(f"✓ ConfigurationError: {e.message}")
        print(f"  Status: {e.status_code}, Code: {e.error_code}")
        print(f"  Details: {e.details}\n")


def test_error_schemas():
    """Test error response schemas."""
    print("\nTesting error response schemas...\n")

    # Create error response
    error_detail = ErrorDetail(
        code="INVALID_PROVIDER",
        message="Invalid provider 'invalid'",
        details={"provider": "invalid", "valid_providers": ["openai", "zai"]},
    )

    error_response = ErrorResponse(error=error_detail, request_id="req_test123")

    print(f"✓ ErrorResponse created:")
    print(f"  {error_response.model_dump_json(indent=2)}\n")


def test_logger():
    """Test logger setup."""
    print("\nTesting logger...\n")

    from src.utils.logger import logger, set_request_id, get_request_id

    # Set request ID
    set_request_id("req_test456")
    print(f"✓ Request ID set: {get_request_id()}")

    # Test logging
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")

    print("✓ Logger working\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Middleware and Error Handling Test Suite")
    print("=" * 60 + "\n")

    try:
        test_exceptions()
        test_error_schemas()
        test_logger()

        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
