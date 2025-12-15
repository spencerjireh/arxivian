"""Global exception handler for consistent error responses."""

import traceback
from datetime import datetime
from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError

from src.exceptions import BaseAPIException, DatabaseError
from src.schemas.errors import ErrorDetail, ErrorResponse
from src.utils.logger import get_request_id, logger


async def base_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """
    Handle custom API exceptions.

    Args:
        request: FastAPI request
        exc: Custom exception

    Returns:
        JSONResponse with error details
    """
    logger.error(
        f"API Exception: {exc.error_code} - {exc.message}",
        extra={"details": exc.details, "status_code": exc.status_code},
    )

    error_response = ErrorResponse(
        error=ErrorDetail(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
        ),
        request_id=get_request_id(),
        timestamp=datetime.utcnow(),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, PydanticValidationError]
) -> JSONResponse:
    """
    Handle Pydantic validation errors from request parsing.

    Args:
        request: FastAPI request
        exc: Validation error

    Returns:
        JSONResponse with validation error details
    """
    logger.warning(f"Validation error: {exc.errors()}")

    error_response = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": exc.errors()},
        ),
        request_id=get_request_id(),
        timestamp=datetime.utcnow(),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle SQLAlchemy database errors.

    Args:
        request: FastAPI request
        exc: SQLAlchemy error

    Returns:
        JSONResponse with database error details
    """
    logger.error(f"Database error: {str(exc)}", exc_info=True)

    # Convert to our custom exception
    db_error = DatabaseError(
        message="Database operation failed",
        details={"error": str(exc)},
    )

    error_response = ErrorResponse(
        error=ErrorDetail(
            code=db_error.error_code,
            message=db_error.message,
            details=db_error.details,
        ),
        request_id=get_request_id(),
        timestamp=datetime.utcnow(),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: FastAPI request
        exc: Unhandled exception

    Returns:
        JSONResponse with generic error message
    """
    # Log full traceback for debugging
    logger.critical(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        exc_info=True,
        extra={"traceback": traceback.format_exc()},
    )

    error_response = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details={
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        ),
        request_id=get_request_id(),
        timestamp=datetime.utcnow(),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Custom exceptions
    app.add_exception_handler(BaseAPIException, base_exception_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)

    # Database errors
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

    # Catch-all for unexpected errors
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered")
