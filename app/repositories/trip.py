from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.entities import Booking, TravelPreference, Trip
from app.models.enums import BookingStatus, BookingType, TripStatus
from app.schemas.trip import (
    BookingCreate,
    BookingUpdate,
    TravelPreferenceUpdate,
    TripCreate,
    TripUpdate,
)


class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: TripCreate) -> Trip:
        trip = Trip(
            name=data.name,
            start_date=data.start_date,
            end_date=data.end_date,
            base_currency=data.base_currency,
            home_timezone=data.home_timezone,
            status=TripStatus.PLANNING,
        )
        self.session.add(trip)
        await self.session.flush()
        pref = TravelPreference(trip_id=trip.id)
        self.session.add(pref)
        await self.session.flush()
        await self.session.refresh(trip)
        return trip

    async def list_trips(self) -> list[Trip]:
        result = await self.session.execute(select(Trip).order_by(Trip.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, trip_id: UUID) -> Trip | None:
        result = await self.session.execute(select(Trip).where(Trip.id == trip_id))
        return result.scalar_one_or_none()

    async def update(self, trip: Trip, data: TripUpdate) -> Trip:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(trip, field, value)
        if trip.end_date < trip.start_date:
            raise AppError("VALIDATION_ERROR", "end_date must be on or after start_date")
        await self.session.flush()
        await self.session.refresh(trip)
        return trip

    async def get_preferences(self, trip_id: UUID) -> TravelPreference | None:
        result = await self.session.execute(
            select(TravelPreference).where(TravelPreference.trip_id == trip_id)
        )
        return result.scalar_one_or_none()

    async def update_preferences(
        self, pref: TravelPreference, data: TravelPreferenceUpdate
    ) -> TravelPreference:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(pref, field, value)
        await self.session.flush()
        await self.session.refresh(pref)
        return pref


class BookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, trip_id: UUID, data: BookingCreate, status: BookingStatus) -> Booking:
        booking = Booking(
            trip_id=trip_id,
            type=data.type,
            provider=data.provider,
            title=data.title,
            confirmation_code=data.confirmation_code,
            start_at=data.start_at,
            end_at=data.end_at,
            timezone=data.timezone,
            latitude=data.latitude,
            longitude=data.longitude,
            cost_amount=data.cost_amount,
            currency=data.currency,
            location_name=data.location_name,
            status=status,
        )
        self.session.add(booking)
        await self.session.flush()
        await self.session.refresh(booking)
        return booking

    async def list_by_trip(
        self, trip_id: UUID, status: BookingStatus | None = None
    ) -> list[Booking]:
        query = select(Booking).where(Booking.trip_id == trip_id).order_by(Booking.start_at)
        if status:
            query = query.where(Booking.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, booking_id: UUID) -> Booking | None:
        result = await self.session.execute(select(Booking).where(Booking.id == booking_id))
        return result.scalar_one_or_none()

    async def update(self, booking: Booking, data: BookingUpdate) -> Booking:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(booking, field, value)
        await self.session.flush()
        await self.session.refresh(booking)
        return booking

    async def find_duplicates(
        self,
        trip_id: UUID,
        confirmation_code: str | None,
        provider: str | None,
        title: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[Booking]:
        query = select(Booking).where(
            Booking.trip_id == trip_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.EXTRACTED]),
        )
        result = await self.session.execute(query)
        candidates = list(result.scalars().all())
        duplicates: list[Booking] = []
        for b in candidates:
            if confirmation_code and b.confirmation_code == confirmation_code:
                duplicates.append(b)
            elif provider and b.provider == provider and b.title == title:
                duplicates.append(b)
            elif b.start_at == start_at and b.end_at == end_at and b.title == title:
                duplicates.append(b)
        return duplicates

    async def get_confirmed_for_date(self, trip_id: UUID, target_date: date) -> list[Booking]:
        result = await self.session.execute(
            select(Booking).where(
                Booking.trip_id == trip_id,
                Booking.status == BookingStatus.CONFIRMED,
            )
        )
        bookings = list(result.scalars().all())
        return [
            b
            for b in bookings
            if b.start_at.date() <= target_date <= b.end_at.date()
            or b.start_at.date() == target_date
        ]
