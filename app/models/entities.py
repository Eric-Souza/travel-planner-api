import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.session import Base
from app.models.enums import (
    BookingStatus,
    BookingType,
    DocumentProcessingStatus,
    DocumentType,
    ItineraryItemStatus,
    MessageRole,
    ProposalStatus,
    TripStatus,
)

if TYPE_CHECKING:
    pass

EMBEDDING_DIM = 768


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="USD")
    home_timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    status: Mapped[TripStatus] = mapped_column(Enum(TripStatus), default=TripStatus.PLANNING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    preferences: Mapped["TravelPreference | None"] = relationship(back_populates="trip", uselist=False)
    bookings: Mapped[list["Booking"]] = relationship(back_populates="trip")
    documents: Mapped[list["Document"]] = relationship(back_populates="trip")
    places: Mapped[list["Place"]] = relationship(back_populates="trip")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="trip")


class TravelPreference(Base):
    __tablename__ = "travel_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), unique=True
    )
    budget_level: Mapped[str | None] = mapped_column(String(32))
    pace: Mapped[str | None] = mapped_column(String(32))
    interests: Mapped[list | None] = mapped_column(JSONB)
    food_preferences: Mapped[list | None] = mapped_column(JSONB)
    nightlife_interest: Mapped[int | None] = mapped_column(Integer)
    hiking_interest: Mapped[int | None] = mapped_column(Integer)
    skiing_interest: Mapped[int | None] = mapped_column(Integer)
    max_walking_minutes: Mapped[int | None] = mapped_column(Integer)
    preferred_start_time: Mapped[str | None] = mapped_column(String(8))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    trip: Mapped["Trip"] = relationship(back_populates="preferences")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    type: Mapped[BookingType] = mapped_column(Enum(BookingType), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    confirmation_code: Mapped[str | None] = mapped_column(String(128))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    cost_amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.CONFIRMED)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    traveler_names: Mapped[list | None] = mapped_column(JSONB)
    location_name: Mapped[str | None] = mapped_column(String(512))
    cancellation_policy: Mapped[str | None] = mapped_column(Text)
    uncertainty_notes: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    trip: Mapped["Trip"] = relationship(back_populates="bookings")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    document_type: Mapped[DocumentType | None] = mapped_column(Enum(DocumentType))
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(DocumentProcessingStatus), default=DocumentProcessingStatus.UPLOADED
    )
    extracted_text: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    trip: Mapped["Trip"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Place(Base):
    __tablename__ = "places"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    address: Mapped[str | None] = mapped_column(String(1024))
    source: Mapped[str | None] = mapped_column(String(64))
    user_saved: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trip: Mapped["Trip"] = relationship(back_populates="places")


class ItineraryVersion(Base):
    __tablename__ = "itinerary_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["ItineraryItem"]] = relationship(back_populates="version")


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("itinerary_versions.id", ondelete="CASCADE")
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[str | None] = mapped_column(String(8))
    end_time: Mapped[str | None] = mapped_column(String(8))
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ItineraryItemStatus] = mapped_column(
        Enum(ItineraryItemStatus), default=ItineraryItemStatus.SUGGESTED
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL")
    )
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="SET NULL")
    )
    warnings: Mapped[list | None] = mapped_column(JSONB)
    source_refs: Mapped[list | None] = mapped_column(JSONB)
    cost_amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    weather_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    version: Mapped["ItineraryVersion"] = relationship(back_populates="items")


class ItineraryProposal(Base):
    __tablename__ = "itinerary_proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    status: Mapped[ProposalStatus] = mapped_column(Enum(ProposalStatus), default=ProposalStatus.PENDING)
    rainy_day_date: Mapped[date | None] = mapped_column(Date)
    warnings: Mapped[list | None] = mapped_column(JSONB)
    sources: Mapped[list | None] = mapped_column(JSONB)
    before_items: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["ItineraryProposalItem"]] = relationship(back_populates="proposal")


class ItineraryProposalItem(Base):
    __tablename__ = "itinerary_proposal_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("itinerary_proposals.id", ondelete="CASCADE")
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[str | None] = mapped_column(String(8))
    end_time: Mapped[str | None] = mapped_column(String(8))
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ItineraryItemStatus] = mapped_column(
        Enum(ItineraryItemStatus), default=ItineraryItemStatus.SUGGESTED
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    place_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    warnings: Mapped[list | None] = mapped_column(JSONB)
    source_refs: Mapped[list | None] = mapped_column(JSONB)
    cost_amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    weather_note: Mapped[str | None] = mapped_column(Text)

    proposal: Mapped["ItineraryProposal"] = relationship(back_populates="items")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    trip: Mapped["Trip"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list | None] = mapped_column(JSONB)
    tool_results: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(32), default="complete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class ToolRun(Base):
    __tablename__ = "tool_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trip_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments: Mapped[dict | None] = mapped_column(JSONB)
    result_summary: Mapped[str | None] = mapped_column(Text)
    result_data: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(32), default="success")
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    trip_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    details: Mapped[dict | None] = mapped_column(JSONB)
    model_name: Mapped[str | None] = mapped_column(String(128))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
