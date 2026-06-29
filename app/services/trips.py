import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.tables import Booking, TravelPreference, Trip
from app.schemas import (
    BookingCreate,
    BookingRead,
    BookingStatus,
    BookingUpdate,
    PreferenceRead,
    PreferenceUpdate,
    TripCreate,
    TripRead,
    TripSummary,
    TripUpdate,
)


class TripService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_trip(self, data: TripCreate) -> TripRead:
        if data.end_date < data.start_date:
            raise ValidationError("end_date must be on or after start_date")
        trip = Trip(
            name=data.name,
            start_date=data.start_date,
            end_date=data.end_date,
            base_currency=data.base_currency,
            home_timezone=data.home_timezone,
            status=data.status,
        )
        self.session.add(trip)
        await self.session.flush()
        pref = TravelPreference(trip_id=trip.id)
        self.session.add(pref)
        await self.session.flush()
        await self.session.refresh(trip)
        return TripRead.model_validate(trip)

    async def list_trips(self) -> list[TripSummary]:
        result = await self.session.execute(select(Trip).order_by(Trip.created_at.desc()))
        trips = list(result.scalars().all())
        summaries: list[TripSummary] = []
        for trip in trips:
            bc = await self.session.scalar(
                select(func.count()).select_from(Booking).where(Booking.trip_id == trip.id)
            )
            summaries.append(
                TripSummary(
                    **TripRead.model_validate(trip).model_dump(),
                    booking_count=bc or 0,
                    document_count=0,
                )
            )
        return summaries

    async def get_trip(self, trip_id: str) -> TripRead:
        trip = await self._get_trip(trip_id)
        return TripRead.model_validate(trip)

    async def update_trip(self, trip_id: str, data: TripUpdate) -> TripRead:
        trip = await self._get_trip(trip_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(trip, field, value)
        if trip.end_date < trip.start_date:
            raise ValidationError("end_date must be on or after start_date")
        await self.session.flush()
        await self.session.refresh(trip)
        return TripRead.model_validate(trip)

    async def get_preferences(self, trip_id: str) -> PreferenceRead:
        await self._get_trip(trip_id)
        pref = await self._get_preferences(trip_id)
        return PreferenceRead.model_validate(pref)

    async def update_preferences(self, trip_id: str, data: PreferenceUpdate) -> PreferenceRead:
        await self._get_trip(trip_id)
        pref = await self._get_preferences(trip_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(pref, field, value)
        await self.session.flush()
        await self.session.refresh(pref)
        return PreferenceRead.model_validate(pref)

    async def _get_trip(self, trip_id: str) -> Trip:
        result = await self.session.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one_or_none()
        if not trip:
            raise NotFoundError("Trip", trip_id)
        return trip

    async def _get_preferences(self, trip_id: str) -> TravelPreference:
        result = await self.session.execute(
            select(TravelPreference).where(TravelPreference.trip_id == trip_id)
        )
        pref = result.scalar_one_or_none()
        if not pref:
            raise NotFoundError("TravelPreference", trip_id)
        return pref


class BookingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.trips = TripService(session)

    def _validate_dates(self, trip: Trip, start_at: datetime, end_at: datetime) -> None:
        if end_at <= start_at:
            raise ValidationError(
                "The booking end time must be after the start time.",
                details=[{"field": "end_at", "message": "Must be after start_at"}],
            )
        trip_start = trip.start_date.replace(tzinfo=start_at.tzinfo) if start_at.tzinfo else trip.start_date
        trip_end = trip.end_date.replace(tzinfo=end_at.tzinfo) if end_at.tzinfo else trip.end_date
        if start_at < trip_start or end_at > trip_end:
            raise ValidationError("Booking dates must fall within the trip date range.")

    async def create_booking(self, trip_id: str, data: BookingCreate) -> BookingRead:
        trip = await self.trips._get_trip(trip_id)
        self._validate_dates(trip, data.start_at, data.end_at)
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
            status=data.status.value,
        )
        await self._check_overlap(trip_id, booking)
        self.session.add(booking)
        await self.session.flush()
        await self.session.refresh(booking)
        return BookingRead.model_validate(booking)

    async def list_bookings(self, trip_id: str, status: str | None = None) -> list[BookingRead]:
        await self.trips._get_trip(trip_id)
        query = select(Booking).where(Booking.trip_id == trip_id).order_by(Booking.start_at)
        if status:
            query = query.where(Booking.status == status)
        result = await self.session.execute(query)
        return [BookingRead.model_validate(b) for b in result.scalars().all()]

    async def update_booking(self, booking_id: str, data: BookingUpdate) -> BookingRead:
        booking = await self._get_booking(booking_id)
        trip = await self.trips._get_trip(booking.trip_id)
        start_at = data.start_at or booking.start_at
        end_at = data.end_at or booking.end_at
        self._validate_dates(trip, start_at, end_at)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(booking, field, value)
        if booking.status == BookingStatus.CONFIRMED.value:
            await self._check_overlap(booking.trip_id, booking, exclude_id=booking.id)
        await self.session.flush()
        await self.session.refresh(booking)
        return BookingRead.model_validate(booking)

    async def confirm_booking(self, booking_id: str) -> BookingRead:
        booking = await self._get_booking(booking_id)
        if booking.status not in (BookingStatus.EXTRACTED.value, BookingStatus.CONFLICT.value):
            raise ValidationError("Only extracted or conflict bookings can be confirmed.")
        trip = await self.trips._get_trip(booking.trip_id)
        self._validate_dates(trip, booking.start_at, booking.end_at)
        booking.status = BookingStatus.CONFIRMED.value
        await self._check_overlap(booking.trip_id, booking, exclude_id=booking.id)
        await self.session.flush()
        await self.session.refresh(booking)
        return BookingRead.model_validate(booking)

    async def reject_booking(self, booking_id: str) -> BookingRead:
        booking = await self._get_booking(booking_id)
        booking.status = BookingStatus.REJECTED.value
        await self.session.flush()
        await self.session.refresh(booking)
        return BookingRead.model_validate(booking)

    async def _get_booking(self, booking_id: str) -> Booking:
        result = await self.session.execute(select(Booking).where(Booking.id == booking_id))
        booking = result.scalar_one_or_none()
        if not booking:
            raise NotFoundError("Booking", booking_id)
        return booking

    async def _check_overlap(
        self, trip_id: str, booking: Booking, exclude_id: str | None = None
    ) -> None:
        result = await self.session.execute(
            select(Booking).where(
                Booking.trip_id == trip_id,
                Booking.status == BookingStatus.CONFIRMED.value,
            )
        )
        for other in result.scalars().all():
            if exclude_id and other.id == exclude_id:
                continue
            if booking.start_at < other.end_at and booking.end_at > other.start_at:
                if booking.status == BookingStatus.CONFIRMED.value:
                    raise ConflictError("Booking overlaps with an existing confirmed booking.")
                booking.status = BookingStatus.CONFLICT.value
