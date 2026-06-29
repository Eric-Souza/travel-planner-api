from datetime import date, datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.models.enums import BookingStatus, BookingType, TripStatus
from app.schemas.common import APIModel


class TripCreate(APIModel):
    name: str = Field(min_length=1, max_length=255)
    start_date: date
    end_date: date
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    home_timezone: str = Field(default="UTC", max_length=64)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, end_date: date, info) -> date:
        start = info.data.get("start_date")
        if start and end_date < start:
            raise ValueError("end_date must be on or after start_date")
        return end_date


class TripUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    base_currency: str | None = Field(default=None, min_length=3, max_length=3)
    home_timezone: str | None = Field(default=None, max_length=64)
    status: TripStatus | None = None


class TripResponse(APIModel):
    id: UUID
    name: str
    start_date: date
    end_date: date
    base_currency: str
    home_timezone: str
    status: TripStatus
    created_at: datetime
    updated_at: datetime


class TripListResponse(APIModel):
    trips: list[TripResponse]
    total: int


class TravelPreferenceUpdate(APIModel):
    budget_level: str | None = None
    pace: str | None = None
    interests: list[str] | None = None
    food_preferences: list[str] | None = None
    nightlife_interest: int | None = Field(default=None, ge=0, le=10)
    hiking_interest: int | None = Field(default=None, ge=0, le=10)
    skiing_interest: int | None = Field(default=None, ge=0, le=10)
    max_walking_minutes: int | None = Field(default=None, ge=0)
    preferred_start_time: str | None = None
    notes: str | None = None


class TravelPreferenceResponse(APIModel):
    id: UUID
    trip_id: UUID
    budget_level: str | None
    pace: str | None
    interests: list[str] | None
    food_preferences: list[str] | None
    nightlife_interest: int | None
    hiking_interest: int | None
    skiing_interest: int | None
    max_walking_minutes: int | None
    preferred_start_time: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BookingCreate(APIModel):
    type: BookingType
    provider: str | None = None
    title: str = Field(min_length=1, max_length=512)
    confirmation_code: str | None = None
    start_at: datetime
    end_at: datetime
    timezone: str = "UTC"
    latitude: float | None = None
    longitude: float | None = None
    cost_amount: float | None = None
    currency: str | None = None
    location_name: str | None = None


class BookingUpdate(APIModel):
    type: BookingType | None = None
    provider: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=512)
    confirmation_code: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    cost_amount: float | None = None
    currency: str | None = None
    location_name: str | None = None


class BookingResponse(APIModel):
    id: UUID
    trip_id: UUID
    type: BookingType
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
    status: BookingStatus
    source_document_id: UUID | None
    source_page: int | None
    source_excerpt: str | None
    confidence: float | None
    traveler_names: list[str] | None
    location_name: str | None
    cancellation_policy: str | None
    uncertainty_notes: list[str] | None
    created_at: datetime
    updated_at: datetime


class BookingListResponse(APIModel):
    bookings: list[BookingResponse]
    total: int
