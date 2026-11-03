"""Standard error format and exception handlers (FR-05)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import ErrorBody, ErrorDetail, ErrorResponse

REQUEST_LOCATIONS = {"body", "path", "query"}


def field_name(location: tuple[Any, ...]) -> str:
    """The field an error is about, e.g. ('body', 'severity') -> 'severity'."""
    parts = [str(part) for part in location if part not in REQUEST_LOCATIONS]
    return ".".join(parts) or "body"


def friendly_message(error: dict[str, Any]) -> str:
    """Turn one Pydantic error into a plain-language message."""
    field = field_name(tuple(error["loc"]))
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
    status_code: int, code: str, message: str, details: list[ErrorDetail] | None = None
) -> JSONResponse:
    """Build a response in the standard error format."""
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))


async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Invalid body, path or query input -> 422 validation_error with field details."""
    details = [
        ErrorDetail(field=field_name(tuple(error["loc"])), message=friendly_message(error))
        for error in exc.errors()
    ]
    return error_response(422, "validation_error", "Invalid input.", details)


def register_error_handlers(app: FastAPI) -> None:
    """Attach all error handlers to the app."""
    app.add_exception_handler(RequestValidationError, handle_validation_error)
