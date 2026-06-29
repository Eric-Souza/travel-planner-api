from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.db.session import get_db
from app.schemas import AskDocumentQuestionRequest, SearchRequest
from app.services.retrieval import RetrievalService

router = APIRouter(prefix="/trips/{trip_id}", tags=["retrieval"])


@router.post("/search")
async def search_documents(
    trip_id: str, data: SearchRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await RetrievalService(db).search(trip_id, data)
    return success(result.model_dump())


@router.post("/ask-document-question")
async def ask_document_question(
    trip_id: str, data: AskDocumentQuestionRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await RetrievalService(db).ask(trip_id, data)
    return success(result.model_dump())
