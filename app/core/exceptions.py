from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.contracts.api import ErrorItem, ErrorResponse


class AppException(Exception):
    """Expected application error with a stable public contract."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def _error_response(
    request: Request,
    *,
    code: str,
    message: str,
    status_code: int,
    details: Any | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        request_id=request.state.request_id,
        error=ErrorItem(code=code, message=message, details=details),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return _error_response(
        request,
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _error_response(
        request,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=422,
        details=exc.errors(),
    )


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(  # type: ignore[arg-type]
        RequestValidationError, validation_exception_handler
    )

