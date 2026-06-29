from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.db.session import get_db
from app.services.documents import DocumentService

router = APIRouter(tags=["documents"])


@router.post("/trips/{trip_id}/documents")
async def upload_document(
    trip_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    content = await file.read()
    result = await DocumentService(db).upload(
        trip_id, file.filename or "upload.bin", file.content_type or "", content
    )
    return success(result.model_dump())


@router.get("/documents/{document_id}")
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await DocumentService(db).get_document(document_id)
    return success(result.model_dump())


@router.get("/documents/{document_id}/processing-status")
async def processing_status(document_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await DocumentService(db).processing_status(document_id)
    return success(result.model_dump())


@router.post("/documents/{document_id}/process")
async def process_document(document_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await DocumentService(db).process(document_id)
    return success(result.model_dump())


@router.post("/documents/{document_id}/extract-booking")
async def extract_booking(document_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await DocumentService(db).extract_booking(document_id)
    return success(result.model_dump())


@router.get("/documents/{document_id}/booking-candidate")
async def booking_candidate(document_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await DocumentService(db).booking_candidate(document_id)
    return success(result.model_dump())


@router.post("/documents/{document_id}/embed")
async def embed_document(document_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    count = await DocumentService(db).embed_document(document_id)
    return success({"document_id": document_id, "chunks_created": count})
