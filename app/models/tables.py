import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="USD")
    home_timezone: Mapped[str] = mapped_column(String(64), default="America/Argentina/Buenos_Aires")
    status: Mapped[str] = mapped_column(String(32), default="active")
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

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id", ondelete="CASCADE"), unique=True)
    budget_level: Mapped[str] = mapped_column(String(32), default="moderate")
    pace: Mapped[str] = mapped_column(String(32), default="moderate")
    interests: Mapped[str | None] = mapped_column(Text)
    food_preferences: Mapped[str | None] = mapped_column(Text)
    nightlife_interest: Mapped[int] = mapped_column(Integer, default=3)
    hiking_interest: Mapped[int] = mapped_column(Integer, default=3)
    skiing_interest: Mapped[int] = mapped_column(Integer, default=1)
    max_walking_minutes: Mapped[int] = mapped_column(Integer, default=30)
    preferred_start_time: Mapped[str | None] = mapped_column(String(8))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    trip: Mapped["Trip"] = relationship(back_populates="preferences")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(64))
    processing_status: Mapped[str] = mapped_column(String(32), default="uploaded")
    extracted_text: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    trip: Mapped["Trip"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(32), nullable=False)
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
    status: Mapped[str] = mapped_column(String(32), default="confirmed")
    source_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"))
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    uncertainty_notes: Mapped[str | None] = mapped_column(Text)
    location_name: Mapped[str | None] = mapped_column(String(512))
    cancellation_policy: Mapped[str | None] = mapped_column(Text)
    traveler_names: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    trip: Mapped["Trip"] = relationship(back_populates="bookings")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"))
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id", ondelete="CASCADE"))
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[str | None] = mapped_column(Text)
    embedding_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Place(Base):
    __tablename__ = "places"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="attraction")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    address: Mapped[str | None] = mapped_column(String(1024))
    source: Mapped[str] = mapped_column(String(64), default="user")
    user_saved: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    trip: Mapped["Trip"] = relationship(back_populates="places")


class ItineraryVersion(Base):
    __tablename__ = "itinerary_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["ItineraryItem"]] = relationship(back_populates="version")


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    itinerary_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("itinerary_versions.id", ondelete="CASCADE")
    )
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id", ondelete="CASCADE"))
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    start_time: Mapped[str | None] = mapped_column(String(8))
    end_time: Mapped[str | None] = mapped_column(String(8))
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    place_id: Mapped[str | None] = mapped_column(String(36))
    booking_id: Mapped[str | None] = mapped_column(String(36))
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_outdoor: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[str | None] = mapped_column(Text)
    source_refs: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    version: Mapped["ItineraryVersion"] = relationship(back_populates="items")


class ItineraryProposal(Base):
    __tablename__ = "itinerary_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    mode: Mapped[str] = mapped_column(String(32), default="standard")
    target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    warnings_json: Mapped[str | None] = mapped_column(Text)
    before_items_json: Mapped[str | None] = mapped_column(Text)
    items_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    trip: Mapped["Trip"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="complete")
    sources_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class ToolRun(Base):
    __tablename__ = "tool_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trip_id: Mapped[str | None] = mapped_column(String(36))
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments_json: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="success")
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    trip_id: Mapped[str | None] = mapped_column(String(36))
    details_json: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str | None] = mapped_column(String(128))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
