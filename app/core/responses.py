from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.request_id import get_request_id

T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody
    request_id: str


class DataResponse(BaseModel, Generic[T]):
    data: T
    request_id: str


def success(data: Any) -> dict[str, Any]:
    return {"data": data, "request_id": get_request_id()}


def error_response(
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        },
        "request_id": get_request_id(),
    }
