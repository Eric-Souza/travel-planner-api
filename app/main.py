from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import v1_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.core.responses import success
from app.db.init_db import init_db
from app.db.session import engine
from app.schemas import HealthResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)
    await init_db(engine)
    yield


app = FastAPI(
    title="Travel Planner API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(v1_router)


@app.get("/health")
async def root_health() -> dict:
    data = HealthResponse(
        status="ok",
        app_env=settings.app_env,
        database="sqlite" if settings.is_sqlite else "postgresql",
    )
    return success(data.model_dump())
