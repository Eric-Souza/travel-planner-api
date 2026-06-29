from typing import Any

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(APIModel):
    status: str
    environment: str


class ErrorDetail(APIModel):
    field: str
    message: str
