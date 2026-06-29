from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class PlaceCreate(APIModel):
    name: str = Field(min_length=1, max_length=512)
    category: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    source: str | None = "user"


class PlaceResponse(APIModel):
    id: UUID
    trip_id: UUID
    name: str
    category: str | None
    latitude: float | None
    longitude: float | None
    address: str | None
    source: str | None
    user_saved: bool
    created_at: datetime


class PlaceSearchRequest(APIModel):
    query: str = Field(min_length=1)
    latitude: float | None = None
    longitude: float | None = None
    category: str | None = None


class WeatherResult(APIModel):
    date: date
    condition: str
    temperature_high: float
    temperature_low: float
    precipitation_chance: float
    fetched_at: datetime
    cache_hit: bool = False


class ExchangeRateResult(APIModel):
    from_currency: str
    to_currency: str
    rate: float
    reference_date: date
    fetched_at: datetime
    cache_hit: bool = False


class RouteResult(APIModel):
    origin: str
    destination: str
    mode: str
    distance_km: float
    duration_minutes: int
    fetched_at: datetime
    cache_hit: bool = False
