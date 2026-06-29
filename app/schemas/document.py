from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import DocumentProcessingStatus, DocumentType
from app.schemas.common import APIModel


class DocumentResponse(APIModel):
    id: UUID
    trip_id: UUID
    file_name: str
    file_type: str
    mime_type: str
    document_type: DocumentType | None
    processing_status: DocumentProcessingStatus
    error_message: str | None
    uploaded_at: datetime
    processed_at: datetime | None


class ProcessingStatusResponse(APIModel):
    document_id: UUID
    processing_status: DocumentProcessingStatus
    document_type: DocumentType | None
    error_message: str | None
    processed_at: datetime | None


class DocumentProcessResponse(APIModel):
    document_id: UUID
    processing_status: DocumentProcessingStatus
    pages_extracted: int | None = None
    text_length: int | None = None


class BookingEvidence(APIModel):
    field_name: str
    excerpt: str
    page: int | None = None


class BookingExtraction(APIModel):
    type: str
    provider: str | None = None
    title: str
    traveler_names: list[str] | None = None
    confirmation_code: str | None = None
    start_at: str
    end_at: str
    timezone: str = "UTC"
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    total_amount: float | None = None
    currency: str | None = None
    cancellation_policy: str | None = None
    source_evidence: list[BookingEvidence] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty_notes: list[str] = Field(default_factory=list)


class DocumentClassification(APIModel):
    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None


class BookingCandidateResponse(APIModel):
    booking_id: UUID | None
    document_id: UUID
    extraction: BookingExtraction | None
    is_duplicate: bool = False
    duplicate_booking_id: UUID | None = None
    status: str


class ExtractBookingResponse(APIModel):
    document_id: UUID
    booking_id: UUID
    status: str
    is_duplicate: bool = False
