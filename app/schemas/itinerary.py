from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import ItineraryItemStatus
from app.schemas.common import APIModel


class SourceCitation(APIModel):
    type: str
    title: str
    page: int | None = None
    excerpt: str
    source_id: str
    fetched_at: datetime | None = None


class RetrievedChunk(APIModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    page_number: int | None
    section_title: str | None
    content: str
    excerpt: str
    score: float


class SearchRequest(APIModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResponse(APIModel):
    chunks: list[RetrievedChunk]
    total: int


class AskDocumentQuestionRequest(APIModel):
    question: str = Field(min_length=1)


class GroundedAnswer(APIModel):
    answer: str
    found: bool
    sources: list[SourceCitation]
    confidence: float | None = None


class ProposalItemSchema(APIModel):
    date: date
    start_time: str | None = None
    end_time: str | None = None
    title: str
    description: str | None = None
    status: ItineraryItemStatus = ItineraryItemStatus.SUGGESTED
    is_locked: bool = False
    booking_id: UUID | None = None
    place_id: UUID | None = None
    warnings: list[str] = Field(default_factory=list)
    source_refs: list[dict] = Field(default_factory=list)
    cost_amount: float | None = None
    currency: str | None = None
    weather_note: str | None = None


class ItineraryProposalSchema(APIModel):
    items: list[ProposalItemSchema]
    warnings: list[str] = Field(default_factory=list)
    sources: list[SourceCitation] = Field(default_factory=list)


class ItineraryProposalRequest(APIModel):
    rainy_day_date: date | None = None


class ItineraryProposalResponse(APIModel):
    id: UUID
    trip_id: UUID
    status: str
    items: list[ProposalItemSchema]
    warnings: list[str]
    sources: list[SourceCitation]
    rainy_day_date: date | None
    before_items: list[ProposalItemSchema] | None
    created_at: datetime


class ItineraryItemResponse(APIModel):
    id: UUID
    date: date
    start_time: str | None
    end_time: str | None
    title: str
    description: str | None
    status: ItineraryItemStatus
    is_locked: bool
    booking_id: UUID | None
    place_id: UUID | None
    warnings: list[str] | None
    cost_amount: float | None
    currency: str | None
    weather_note: str | None


class ItineraryVersionResponse(APIModel):
    id: UUID
    trip_id: UUID
    version_number: int
    is_active: bool
    items: list[ItineraryItemResponse]
    created_at: datetime


class ApplyProposalResponse(APIModel):
    proposal_id: UUID
    version_id: UUID
    items_applied: int
