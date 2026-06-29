from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.errors import AppError
from app.models.entities import Booking
from app.models.enums import BookingStatus, BookingType, DocumentProcessingStatus, DocumentType
from app.repositories.document import DocumentRepository
from app.repositories.trip import BookingRepository, TripRepository
from app.schemas.document import (
    BookingCandidateResponse,
    BookingExtraction,
    DocumentClassification,
    ExtractBookingResponse,
)
from app.services.llm.ollama import get_llm_provider
from app.services.llm.prompts.document import CLASSIFICATION_PROMPT, EXTRACTION_PROMPT


class ExtractionService:
    def __init__(self, session) -> None:
        self.session = session
        self.docs = DocumentRepository(session)
        self.bookings = BookingRepository(session)
        self.trips = TripRepository(session)
        self.llm = get_llm_provider()

    async def classify_document(self, document_id: UUID) -> DocumentClassification:
        doc = await self._get_parsed_doc(document_id)
        prompt = CLASSIFICATION_PROMPT.format(content=doc.extracted_text[:8000])
        return await self.llm.structured_output(
            [{"role": "user", "content": prompt}], DocumentClassification
        )

    async def extract_booking(self, document_id: UUID) -> ExtractBookingResponse:
        doc = await self._get_parsed_doc(document_id)
        await self.docs.update_status(doc, DocumentProcessingStatus.EXTRACTING)
        classification = await self.classify_document(document_id)
        doc.document_type = classification.document_type
        prompt = EXTRACTION_PROMPT.format(content=doc.extracted_text[:12000])
        extraction = await self.llm.structured_output(
            [{"role": "user", "content": prompt}], BookingExtraction
        )
        booking_type = self._map_booking_type(classification.document_type)
        start_at = datetime.fromisoformat(extraction.start_at.replace("Z", "+00:00"))
        end_at = datetime.fromisoformat(extraction.end_at.replace("Z", "+00:00"))
        duplicates = await self.bookings.find_duplicates(
            doc.trip_id,
            extraction.confirmation_code,
            extraction.provider,
            extraction.title,
            start_at,
            end_at,
        )
        status = BookingStatus.CONFLICT if duplicates else BookingStatus.EXTRACTED
        source_excerpt = extraction.source_evidence[0].excerpt if extraction.source_evidence else None
        source_page = extraction.source_evidence[0].page if extraction.source_evidence else None
        booking = Booking(
            trip_id=doc.trip_id,
            type=booking_type,
            provider=extraction.provider,
            title=extraction.title,
            confirmation_code=extraction.confirmation_code,
            start_at=start_at,
            end_at=end_at,
            timezone=extraction.timezone,
            latitude=extraction.latitude,
            longitude=extraction.longitude,
            cost_amount=extraction.total_amount,
            currency=extraction.currency,
            status=status,
            source_document_id=doc.id,
            source_page=source_page,
            source_excerpt=source_excerpt,
            confidence=extraction.confidence,
            traveler_names=extraction.traveler_names,
            location_name=extraction.location_name,
            cancellation_policy=extraction.cancellation_policy,
            uncertainty_notes=extraction.uncertainty_notes,
        )
        self.session.add(booking)
        doc.processing_status = DocumentProcessingStatus.EXTRACTED
        await self.session.flush()
        await self.session.refresh(booking)
        return ExtractBookingResponse(
            document_id=doc.id,
            booking_id=booking.id,
            status=booking.status.value,
            is_duplicate=bool(duplicates),
        )

    async def get_booking_candidate(self, document_id: UUID) -> BookingCandidateResponse:
        doc = await self.docs.get_by_id(document_id)
        if not doc:
            raise AppError("NOT_FOUND", f"Document {document_id} not found", status_code=404)
        bookings = await self.bookings.list_by_trip(doc.trip_id, BookingStatus.EXTRACTED)
        booking = next((b for b in bookings if b.source_document_id == doc.id), None)
        if not booking:
            conflict = await self.bookings.list_by_trip(doc.trip_id, BookingStatus.CONFLICT)
            booking = next((b for b in conflict if b.source_document_id == doc.id), None)
        if not booking:
            return BookingCandidateResponse(
                booking_id=None,
                document_id=doc.id,
                extraction=None,
                status="not_extracted",
            )
        extraction = BookingExtraction(
            type=booking.type.value,
            provider=booking.provider,
            title=booking.title,
            traveler_names=booking.traveler_names,
            confirmation_code=booking.confirmation_code,
            start_at=booking.start_at.isoformat(),
            end_at=booking.end_at.isoformat(),
            timezone=booking.timezone,
            location_name=booking.location_name,
            latitude=booking.latitude,
            longitude=booking.longitude,
            total_amount=booking.cost_amount,
            currency=booking.currency,
            cancellation_policy=booking.cancellation_policy,
            source_evidence=[],
            confidence=booking.confidence or 0.0,
            uncertainty_notes=booking.uncertainty_notes or [],
        )
        duplicates = await self.bookings.find_duplicates(
            doc.trip_id,
            booking.confirmation_code,
            booking.provider,
            booking.title,
            booking.start_at,
            booking.end_at,
        )
        dup_id = duplicates[0].id if duplicates and duplicates[0].id != booking.id else None
        return BookingCandidateResponse(
            booking_id=booking.id,
            document_id=doc.id,
            extraction=extraction,
            is_duplicate=bool(dup_id),
            duplicate_booking_id=dup_id,
            status=booking.status.value,
        )

    async def _get_parsed_doc(self, document_id: UUID):
        doc = await self.docs.get_by_id(document_id)
        if not doc:
            raise AppError("NOT_FOUND", f"Document {document_id} not found", status_code=404)
        if not doc.extracted_text:
            raise AppError("VALIDATION_ERROR", "Document must be parsed before extraction")
        return doc

    def _map_booking_type(self, doc_type: DocumentType) -> BookingType:
        mapping = {
            DocumentType.HOTEL_RESERVATION: BookingType.HOTEL,
            DocumentType.FLIGHT_TICKET: BookingType.FLIGHT,
            DocumentType.TRAIN_TICKET: BookingType.TRAIN,
            DocumentType.BUS_TICKET: BookingType.BUS,
            DocumentType.ACTIVITY_BOOKING: BookingType.ACTIVITY,
            DocumentType.RESTAURANT_RESERVATION: BookingType.RESTAURANT,
        }
        return mapping.get(doc_type, BookingType.OTHER)
