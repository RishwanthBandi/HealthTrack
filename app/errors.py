"""Standard error format and exception handlers (FR-05)."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.schemas import DATABASE_ERROR_MESSAGE, ErrorBody, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

REQUEST_LOCATIONS = {"body", "path", "query"}
INTERNAL_ERROR_MESSAGE = "Something went wrong on our side. Please try again later."
HTTP_ERRORS = {
    404: ("not_found", "The requested URL was not found."),
    405: ("method_not_allowed", "This HTTP method is not allowed for this URL."),
}


def field_name(error: dict[str, Any]) -> str:
    """The field an error is about, e.g. ('body', 'severity') -> 'severity'."""
    if error["type"] == "json_invalid":
        return "body"
    parts = [str(part) for part in error["loc"] if part not in REQUEST_LOCATIONS]
    return ".".join(parts) or "body"


def friendly_message(error: dict[str, Any]) -> str:
    """Turn one Pydantic error into a plain-language message."""
    field = field_name(error)
    error_type = error["type"]
    if error_type == "missing":
        return f"{field} is required"
    if error_type in {"int_parsing", "int_type", "greater_than"}:
        return f"{field} must be a positive whole number"
    if error_type == "less_than_equal":
        return f"{field} must be at most {error['ctx']['le']}"
    if error_type == "json_invalid":
        return "the request body is not valid JSON"
    return error["msg"]


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build a response in the standard error format."""
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(
        status_code=status_code, content=body.model_dump(exclude_none=True), headers=headers
    )


async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Invalid body, path or query input -> 422 validation_error with field details."""
    details = [
        ErrorDetail(field=field_name(error), message=friendly_message(error))
        for error in exc.errors()
    ]
    return error_response(422, "validation_error", "Invalid input.", details)


async def handle_http_error(_request: Request, exc: HTTPException) -> JSONResponse:
    """Unknown URL -> 404 not_found; wrong method -> 405 method_not_allowed."""
    code, message = HTTP_ERRORS.get(exc.status_code, ("http_error", str(exc.detail)))
    return error_response(exc.status_code, code, message, headers=exc.headers)


async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Any database failure -> 500 database_error. The real error is only logged."""
    logger.error("Database error on %s %s", request.method, request.url.path, exc_info=exc)
    return error_response(500, "database_error", DATABASE_ERROR_MESSAGE)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Any other error -> 500 internal_error. The real error is only logged."""
    logger.error("Unexpected error on %s %s", request.method, request.url.path, exc_info=exc)
    return error_response(500, "internal_error", INTERNAL_ERROR_MESSAGE)


def register_error_handlers(app: FastAPI) -> None:
    """Attach all error handlers to the app."""
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(SQLAlchemyError, handle_database_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
