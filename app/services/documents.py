import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.tables import Booking, Document, DocumentChunk
from app.schemas import (
    BookingCandidateResponse,
    BookingEvidence,
    BookingExtraction,
    BookingRead,
    BookingStatus,
    DocumentClassification,
    DocumentProcessingStatus,
    DocumentRead,
    DocumentType,
    ProcessingStatusRead,
)
from app.services.ingestion.parser import (
    chunk_document,
    parse_document,
    safe_filename,
    validate_upload,
)
from app.services.llm.ollama import get_llm_provider
from app.services.llm.prompts.document import CLASSIFICATION_PROMPT, EXTRACTION_PROMPT

settings = get_settings()


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.llm = get_llm_provider()

    async def upload(self, trip_id: str, filename: str, mime_type: str, content: bytes) -> DocumentRead:
        from app.services.trips import TripService

        await TripService(self.session)._get_trip(trip_id)
        validate_upload(filename, mime_type, len(content))
        ext = Path(filename).suffix.lower().lstrip(".")
        doc_id = str(uuid.uuid4())
        upload_dir = Path(settings.uploads_dir) / trip_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        storage_path = upload_dir / f"{doc_id}_{safe_filename(filename)}"
        storage_path.write_bytes(content)
        document = Document(
            id=doc_id,
            trip_id=trip_id,
            file_name=filename,
            file_type=ext,
            mime_type=mime_type or "application/octet-stream",
            storage_path=str(storage_path),
            processing_status=DocumentProcessingStatus.UPLOADED.value,
        )
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return DocumentRead.model_validate(document)

    async def get_document(self, document_id: str) -> DocumentRead:
        doc = await self._get_doc(document_id)
        return DocumentRead.model_validate(doc)

    async def processing_status(self, document_id: str) -> ProcessingStatusRead:
        doc = await self._get_doc(document_id)
        return ProcessingStatusRead(
            document_id=doc.id,
            processing_status=doc.processing_status,
            error_message=doc.error_message,
            processed_at=doc.processed_at,
        )

    async def process(self, document_id: str) -> DocumentRead:
        doc = await self._get_doc(document_id)
        if doc.processing_status in (
            DocumentProcessingStatus.PARSED.value,
            DocumentProcessingStatus.READY.value,
            DocumentProcessingStatus.EXTRACTED.value,
        ):
            return DocumentRead.model_validate(doc)
        doc.processing_status = DocumentProcessingStatus.PARSING.value
        await self.session.flush()
        try:
            content = Path(doc.storage_path).read_bytes()
            text, pages = parse_document(doc.file_type, content)
            if not text.strip():
                raise ValidationError("No text could be extracted from document")
            doc.extracted_text = text
            doc.processing_status = DocumentProcessingStatus.PARSED.value
            doc.processed_at = datetime.now(UTC)
            doc.error_message = None
            await self.session.flush()
            await self.session.refresh(doc)
            return DocumentRead.model_validate(doc)
        except Exception as exc:
            doc.processing_status = DocumentProcessingStatus.FAILED.value
            doc.error_message = str(exc)
            await self.session.flush()
            raise ValidationError(f"Failed to parse document: {exc}") from exc

    async def extract_booking(self, document_id: str) -> BookingRead:
        doc = await self._get_parsed(document_id)
        doc.processing_status = DocumentProcessingStatus.EXTRACTING.value
        await self.session.flush()
        classification = await self.llm.structured_output(
            [{"role": "user", "content": CLASSIFICATION_PROMPT.format(content=doc.extracted_text[:8000])}],
            DocumentClassification,
        )
        doc.document_type = classification.document_type.value
        extraction = await self.llm.structured_output(
            [{"role": "user", "content": EXTRACTION_PROMPT.format(content=doc.extracted_text[:12000])}],
            BookingExtraction,
        )
        duplicates = await self._find_duplicates(doc.trip_id, extraction)
        status = BookingStatus.CONFLICT if duplicates else BookingStatus.EXTRACTED
        excerpt = extraction.source_evidence[0].excerpt if extraction.source_evidence else None
        page = extraction.source_evidence[0].page if extraction.source_evidence else None
        booking = Booking(
            trip_id=doc.trip_id,
            type=extraction.type,
            provider=extraction.provider,
            title=extraction.title,
            confirmation_code=extraction.confirmation_code,
            start_at=extraction.start_at,
            end_at=extraction.end_at,
            timezone=extraction.timezone,
            latitude=extraction.latitude,
            longitude=extraction.longitude,
            cost_amount=extraction.total_amount,
            currency=extraction.currency,
            status=status.value,
            source_document_id=doc.id,
            source_page=page,
            source_excerpt=excerpt,
            confidence=extraction.confidence,
            location_name=extraction.location_name,
            cancellation_policy=extraction.cancellation_policy,
            uncertainty_notes=json.dumps(extraction.uncertainty_notes),
            traveler_names=json.dumps(extraction.traveler_names),
        )
        self.session.add(booking)
        doc.processing_status = DocumentProcessingStatus.EXTRACTED.value
        await self.session.flush()
        await self.session.refresh(booking)
        return BookingRead.model_validate(booking)

    async def booking_candidate(self, document_id: str) -> BookingCandidateResponse:
        doc = await self._get_doc(document_id)
        result = await self.session.execute(
            select(Booking).where(
                Booking.trip_id == doc.trip_id,
                Booking.source_document_id == doc.id,
                Booking.status.in_([BookingStatus.EXTRACTED.value, BookingStatus.CONFLICT.value]),
            )
        )
        booking = result.scalar_one_or_none()
        if not booking:
            return BookingCandidateResponse(booking=None, document_id=doc.id, extraction=None)
        notes = json.loads(booking.uncertainty_notes) if booking.uncertainty_notes else []
        travelers = json.loads(booking.traveler_names) if booking.traveler_names else []
        extraction = BookingExtraction(
            type=booking.type,
            provider=booking.provider,
            title=booking.title,
            traveler_names=travelers,
            confirmation_code=booking.confirmation_code,
            start_at=booking.start_at,
            end_at=booking.end_at,
            timezone=booking.timezone,
            location_name=booking.location_name,
            latitude=booking.latitude,
            longitude=booking.longitude,
            total_amount=booking.cost_amount,
            currency=booking.currency,
            cancellation_policy=booking.cancellation_policy,
            source_evidence=[
                BookingEvidence(excerpt=booking.source_excerpt or "", page=booking.source_page)
            ]
            if booking.source_excerpt
            else [],
            confidence=booking.confidence or 0.0,
            uncertainty_notes=notes,
        )
        dup = await self._find_duplicates(doc.trip_id, extraction, exclude_id=booking.id)
        return BookingCandidateResponse(
            booking=BookingRead.model_validate(booking),
            document_id=doc.id,
            extraction=extraction,
            is_duplicate=bool(dup),
            duplicate_booking_id=dup[0].id if dup else None,
        )

    async def embed_document(self, document_id: str) -> int:
        doc = await self._get_parsed(document_id)
        doc.processing_status = DocumentProcessingStatus.EMBEDDING.value
        await self.session.flush()
        content = Path(doc.storage_path).read_bytes()
        _, pages = parse_document(doc.file_type, content)
        chunks_data = chunk_document(doc.extracted_text or "", pages, doc.trip_id, doc.id)
        texts = [c["content"] for c in chunks_data]
        embeddings = await self.llm.embed(texts)
        existing = await self.session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
        for chunk in existing.scalars().all():
            await self.session.delete(chunk)
        for data, embedding in zip(chunks_data, embeddings, strict=True):
            self.session.add(
                DocumentChunk(
                    document_id=doc.id,
                    trip_id=doc.trip_id,
                    page_number=data.get("page_number"),
                    section_title=data.get("section_title"),
                    content=data["content"],
                    chunk_metadata=data.get("chunk_metadata"),
                    embedding_json=json.dumps(embedding),
                )
            )
        doc.processing_status = DocumentProcessingStatus.READY.value
        await self.session.flush()
        return len(chunks_data)

    async def _get_doc(self, document_id: str) -> Document:
        result = await self.session.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError("Document", document_id)
        return doc

    async def _get_parsed(self, document_id: str) -> Document:
        doc = await self._get_doc(document_id)
        if not doc.extracted_text:
            raise ValidationError("Document must be parsed before this operation")
        return doc

    async def _find_duplicates(
        self, trip_id: str, extraction: BookingExtraction, exclude_id: str | None = None
    ) -> list[Booking]:
        result = await self.session.execute(
            select(Booking).where(
                Booking.trip_id == trip_id,
                Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.EXTRACTED.value]),
            )
        )
        dups: list[Booking] = []
        for b in result.scalars().all():
            if exclude_id and b.id == exclude_id:
                continue
            if extraction.confirmation_code and b.confirmation_code == extraction.confirmation_code:
                dups.append(b)
            elif (
                extraction.provider
                and b.provider == extraction.provider
                and b.title == extraction.title
            ):
                dups.append(b)
        return dups
