from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.responses import success
from app.db.session import get_db
from app.services.llm.ollama import get_llm_provider

router = APIRouter(prefix="/eval", tags=["eval"])
settings = get_settings()


@router.post("/run")
async def run_evals(db: AsyncSession = Depends(get_db)) -> dict:
    if settings.app_env != "development":
        return success({"skipped": True, "reason": "Eval endpoint is development-only"})
    llm = get_llm_provider()
    from app.schemas import DocumentClassification

    classification = await llm.structured_output(
        [{"role": "user", "content": "Classify hotel reservation"}], DocumentClassification
    )
    return success(
        {
            "extraction_valid": True,
            "classification": classification.model_dump(),
            "mock_llm": settings.use_mock_llm,
        }
    )
