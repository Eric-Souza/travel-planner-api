from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.core.request_id import get_request_id
from app.core.responses import success
from app.schemas import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health(request: Request) -> dict:
    data = HealthResponse(
        status="ok",
        app_env=settings.app_env,
        database="sqlite" if settings.is_sqlite else "postgresql",
    )
    request.state.request_id = get_request_id()
    return success(data.model_dump())
