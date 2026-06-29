from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class BookingStatus(StrEnum):
    EXTRACTED = "extracted"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CONFLICT = "conflict"


class DocumentProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class DocumentType(StrEnum):
    HOTEL_RESERVATION = "hotel_reservation"
    FLIGHT_TICKET = "flight_ticket"
    TRAIN_TICKET = "train_ticket"
    BUS_TICKET = "bus_ticket"
    ACTIVITY_BOOKING = "activity_booking"
    RESTAURANT_RESERVATION = "restaurant_reservation"
    TRAVEL_NOTE = "travel_note"
    UNKNOWN = "unknown"


class TripCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    start_date: datetime
    end_date: datetime
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    home_timezone: str = Field(default="America/Argentina/Buenos_Aires", max_length=64)
    status: str = "active"


class TripUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    start_date: datetime | None = None
    end_date: datetime | None = None
    base_currency: str | None = Field(default=None, min_length=3, max_length=3)
    home_timezone: str | None = Field(default=None, max_length=64)
    status: str | None = None


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    start_date: datetime
    end_date: datetime
    base_currency: str
    home_timezone: str
    status: str
    created_at: datetime
    updated_at: datetime


class TripSummary(TripRead):
    booking_count: int = 0
    document_count: int = 0


class PreferenceUpdate(BaseModel):
    budget_level: str | None = None
    pace: str | None = None
    interests: str | None = None
    food_preferences: str | None = None
    nightlife_interest: int | None = Field(default=None, ge=1, le=5)
    hiking_interest: int | None = Field(default=None, ge=1, le=5)
    skiing_interest: int | None = Field(default=None, ge=1, le=5)
    max_walking_minutes: int | None = Field(default=None, ge=0)
    preferred_start_time: str | None = None
    notes: str | None = None


class PreferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trip_id: str
    budget_level: str
    pace: str
    interests: str | None
    food_preferences: str | None
    nightlife_interest: int
    hiking_interest: int
    skiing_interest: int
    max_walking_minutes: int
    preferred_start_time: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BookingCreate(BaseModel):
    type: str
    provider: str | None = None
    title: str
    confirmation_code: str | None = None
    start_at: datetime
    end_at: datetime
    timezone: str = "UTC"
    latitude: float | None = None
    longitude: float | None = None
    cost_amount: float | None = None
    currency: str | None = None
    status: BookingStatus = BookingStatus.CONFIRMED


class BookingUpdate(BaseModel):
    type: str | None = None
    provider: str | None = None
    title: str | None = None
    confirmation_code: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    cost_amount: float | None = None
    currency: str | None = None


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trip_id: str
    type: str
    provider: str | None
    title: str
    confirmation_code: str | None
    start_at: datetime
    end_at: datetime
    timezone: str
    latitude: float | None
    longitude: float | None
    cost_amount: float | None
    currency: str | None
    status: str
    source_document_id: str | None
    source_page: int | None
    source_excerpt: str | None
    confidence: float | None
    uncertainty_notes: str | None
    created_at: datetime
    updated_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trip_id: str
    file_name: str
    file_type: str
    mime_type: str
    document_type: str | None
    processing_status: str
    error_message: str | None
    uploaded_at: datetime
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProcessingStatusRead(BaseModel):
    document_id: str
    processing_status: str
    error_message: str | None
    processed_at: datetime | None


class DocumentClassification(BaseModel):
    document_type: DocumentType
    confidence: float = Field(ge=0, le=1)


class BookingEvidence(BaseModel):
    excerpt: str
    page: int | None = None
    field: str | None = None


class BookingExtraction(BaseModel):
    type: str
    provider: str | None = None
    title: str
    traveler_names: list[str] = Field(default_factory=list)
    confirmation_code: str | None = None
    start_at: datetime
    end_at: datetime
    timezone: str = "UTC"
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    total_amount: float | None = None
    currency: str | None = None
    cancellation_policy: str | None = None
    source_evidence: list[BookingEvidence] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainty_notes: list[str] = Field(default_factory=list)


class BookingCandidateResponse(BaseModel):
    booking: BookingRead | None
    document_id: str
    extraction: BookingExtraction | None = None
    is_duplicate: bool = False
    duplicate_booking_id: str | None = None


class SourceCitation(BaseModel):
    type: str
    title: str
    page: int | None = None
    excerpt: str
    source_id: str
    fetched_at: datetime | None = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    page_number: int | None
    section_title: str | None
    content: str
    score: float
    citation: SourceCitation


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResponse(BaseModel):
    query: str
    chunks: list[RetrievedChunk]


class AskDocumentQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: str | None = None


class GroundedAnswer(BaseModel):
    question: str
    answer: str
    found: bool
    sources: list[SourceCitation] = Field(default_factory=list)
    not_found_reason: str | None = None


class PlaceCreate(BaseModel):
    name: str
    category: str = "attraction"
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    user_saved: bool = True


class PlaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trip_id: str
    name: str
    category: str
    latitude: float | None
    longitude: float | None
    address: str | None
    source: str
    user_saved: bool
    created_at: datetime
    updated_at: datetime


class PlaceSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    latitude: float | None = None
    longitude: float | None = None
    category: str | None = None


class PlaceSearchResult(BaseModel):
    name: str
    category: str
    latitude: float
    longitude: float
    address: str
    source: str = "mock"


class ItineraryProposalItemSchema(BaseModel):
    date: str
    start_time: str | None = None
    end_time: str | None = None
    title: str
    description: str | None = None
    is_confirmed: bool = False
    is_locked: bool = False
    is_outdoor: bool = False
    booking_id: str | None = None
    place_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ItineraryProposalCreate(BaseModel):
    mode: str = "standard"
    target_date: datetime | None = None


class ItineraryProposalRead(BaseModel):
    id: str
    trip_id: str
    status: str
    mode: str
    target_date: datetime | None
    items: list[ItineraryProposalItemSchema]
    warnings: list[str] = Field(default_factory=list)
    before_items: list[ItineraryProposalItemSchema] | None = None
    created_at: datetime
    updated_at: datetime


class ItineraryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    itinerary_version_id: str
    trip_id: str
    date: datetime
    start_time: str | None
    end_time: str | None
    title: str
    description: str | None
    place_id: str | None
    booking_id: str | None
    is_confirmed: bool
    is_locked: bool
    is_outdoor: bool
    warnings: str | None
    source_refs: str | None
    created_at: datetime
    updated_at: datetime


class ItineraryVersionRead(BaseModel):
    id: str
    trip_id: str
    version_number: int
    is_active: bool
    items: list[ItineraryItemRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ChatStreamRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trip_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    trip_id: str
    role: str
    content: str
    status: str
    sources: list[SourceCitation] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str
    app_env: str
    database: str
