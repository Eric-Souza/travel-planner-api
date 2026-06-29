from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Document, DocumentChunk
from app.models.enums import DocumentProcessingStatus


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        result = await self.session.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def list_by_trip(self, trip_id: UUID) -> list[Document]:
        result = await self.session.execute(
            select(Document).where(Document.trip_id == trip_id).order_by(Document.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        document: Document,
        status: DocumentProcessingStatus,
        error_message: str | None = None,
    ) -> Document:
        document.processing_status = status
        if error_message:
            document.error_message = error_message
        await self.session.flush()
        await self.session.refresh(document)
        return document

    async def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        self.session.add_all(chunks)
        await self.session.flush()

    async def delete_chunks_for_document(self, document_id: UUID) -> None:
        result = await self.session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        for chunk in result.scalars().all():
            await self.session.delete(chunk)
        await self.session.flush()

    async def search_chunks(self, trip_id: UUID, query: str, limit: int = 10) -> list[DocumentChunk]:
        result = await self.session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.trip_id == trip_id)
            .where(DocumentChunk.content.ilike(f"%{query}%"))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_chunks_by_document(self, document_id: UUID) -> list[DocumentChunk]:
        result = await self.session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        return list(result.scalars().all())
