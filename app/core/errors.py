from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.core.request_id import get_request_id

__all__ = ["AppError", "app_error_handler", "http_exception_handler", "validation_exception_handler"]


def error_envelope(
    code: str,
    message: str,
    request_id: str,
    details: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        },
        "request_id": request_id,
    }


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or get_request_id()


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(exc.code, exc.message, _request_id(request), exc.details),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(code, str(exc.detail), _request_id(request)),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", "Invalid value"),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_envelope(
            "VALIDATION_ERROR",
            "Request validation failed.",
            _request_id(request),
            details,
        ),
    )
