"""Global exception handler for consistent error responses."""

import traceback
from datetime import datetime, timezone
from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError

from src.exceptions import BaseAPIException, DatabaseError
from src.schemas.errors import ErrorDetail, ErrorResponse
from src.utils.logger import get_logger, get_request_id

log = get_logger(__name__)


async def base_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """Handle custom API exceptions."""
    log.error(
        "api exception",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )

    error_response = ErrorResponse(
        error=ErrorDetail(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
        ),
        request_id=get_request_id(),
        timestamp=datetime.now(timezone.utc),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, PydanticValidationError]
) -> JSONResponse:
    """Handle Pydantic validation errors from request parsing."""
    log.warning("validation error", errors=exc.errors())

    # exc.errors() may contain non-serializable objects (e.g. ValueError in ctx),
    # so strip the ctx key which can hold raw exception instances.
    errors = [{k: v for k, v in e.items() if k != "ctx"} for e in exc.errors()]

    error_response = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors},
        ),
        request_id=get_request_id(),
        timestamp=datetime.now(timezone.utc),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json"),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    log.error("database error", error=str(exc), traceback=traceback.format_exc())

    db_error = DatabaseError(message="Database operation failed")

    error_response = ErrorResponse(
        error=ErrorDetail(
            code=db_error.error_code,
            message=db_error.message,
        ),
        request_id=get_request_id(),
        timestamp=datetime.now(timezone.utc),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    log.critical(
        "unhandled exception",
        error_type=type(exc).__name__,
        error=str(exc),
        traceback=traceback.format_exc(),
    )

    error_response = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
        ),
        request_id=get_request_id(),
        timestamp=datetime.now(timezone.utc),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with FastAPI application."""
    app.add_exception_handler(BaseAPIException, base_exception_handler)  # type: ignore[invalid-argument-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[invalid-argument-type]
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)  # type: ignore[invalid-argument-type]
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)  # type: ignore[invalid-argument-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[invalid-argument-type]

    log.info("exception handlers registered")
