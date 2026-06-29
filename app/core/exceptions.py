from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} '{resource_id}' not found.",
            status_code=404,
        )


class ValidationError(AppError):
    def __init__(self, message: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            details=details,
        )


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(code="CONFLICT", message=message, status_code=409)
