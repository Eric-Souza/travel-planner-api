from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.enums import BookingStatus
from app.repositories.trip import BookingRepository, TripRepository
from app.schemas.trip import (
    BookingCreate,
    BookingResponse,
    BookingUpdate,
    TravelPreferenceResponse,
    TravelPreferenceUpdate,
    TripCreate,
    TripResponse,
    TripUpdate,
)


def _require_trip(trip, trip_id: UUID):
    if not trip:
        raise AppError("NOT_FOUND", f"Trip {trip_id} not found", status_code=404)
    return trip


def _require_booking(booking, booking_id: UUID):
    if not booking:
        raise AppError("NOT_FOUND", f"Booking {booking_id} not found", status_code=404)
    return booking


class TripService:
    def __init__(self, session: AsyncSession) -> None:
        self.trips = TripRepository(session)
        self.bookings = BookingRepository(session)
        self.session = session

    async def create_trip(self, data: TripCreate) -> TripResponse:
        trip = await self.trips.create(data)
        return TripResponse.model_validate(trip)

    async def list_trips(self) -> list[TripResponse]:
        trips = await self.trips.list_trips()
        return [TripResponse.model_validate(t) for t in trips]

    async def get_trip(self, trip_id: UUID) -> TripResponse:
        trip = _require_trip(await self.trips.get_by_id(trip_id), trip_id)
        return TripResponse.model_validate(trip)

    async def update_trip(self, trip_id: UUID, data: TripUpdate) -> TripResponse:
        trip = _require_trip(await self.trips.get_by_id(trip_id), trip_id)
        trip = await self.trips.update(trip, data)
        return TripResponse.model_validate(trip)

    async def get_preferences(self, trip_id: UUID) -> TravelPreferenceResponse:
        _require_trip(await self.trips.get_by_id(trip_id), trip_id)
        pref = await self.trips.get_preferences(trip_id)
        if not pref:
            raise AppError("NOT_FOUND", "Preferences not found", status_code=404)
        return TravelPreferenceResponse.model_validate(pref)

    async def update_preferences(
        self, trip_id: UUID, data: TravelPreferenceUpdate
    ) -> TravelPreferenceResponse:
        _require_trip(await self.trips.get_by_id(trip_id), trip_id)
        pref = await self.trips.get_preferences(trip_id)
        if not pref:
            raise AppError("NOT_FOUND", "Preferences not found", status_code=404)
        pref = await self.trips.update_preferences(pref, data)
        return TravelPreferenceResponse.model_validate(pref)


class BookingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.trips = TripRepository(session)
        self.bookings = BookingRepository(session)

    def _validate_booking_dates(self, trip, start_at, end_at) -> None:
        if end_at <= start_at:
            raise AppError(
                "VALIDATION_ERROR",
                "The booking end time must be after the start time.",
                details=[{"field": "end_at", "message": "Must be after start_at"}],
            )
        if start_at.date() < trip.start_date or end_at.date() > trip.end_date:
            raise AppError(
                "VALIDATION_ERROR",
                "Booking dates must fall within the trip date range.",
            )

    async def _check_conflicts(self, trip_id: UUID, booking, exclude_id: UUID | None = None):
        confirmed = await self.bookings.list_by_trip(trip_id, BookingStatus.CONFIRMED)
        for other in confirmed:
            if exclude_id and other.id == exclude_id:
                continue
            if booking.start_at < other.end_at and booking.end_at > other.start_at:
                booking.status = BookingStatus.CONFLICT

    async def create_booking(self, trip_id: UUID, data: BookingCreate) -> BookingResponse:
        trip = _require_trip(await self.trips.get_by_id(trip_id), trip_id)
        self._validate_booking_dates(trip, data.start_at, data.end_at)
        booking = await self.bookings.create(trip_id, data, BookingStatus.CONFIRMED)
        await self._check_conflicts(trip_id, booking)
        return BookingResponse.model_validate(booking)

    async def list_bookings(
        self, trip_id: UUID, status: BookingStatus | None = None
    ) -> list[BookingResponse]:
        _require_trip(await self.trips.get_by_id(trip_id), trip_id)
        bookings = await self.bookings.list_by_trip(trip_id, status)
        return [BookingResponse.model_validate(b) for b in bookings]

    async def update_booking(self, booking_id: UUID, data: BookingUpdate) -> BookingResponse:
        booking = _require_booking(await self.bookings.get_by_id(booking_id), booking_id)
        trip = _require_trip(await self.trips.get_by_id(booking.trip_id), booking.trip_id)
        start_at = data.start_at or booking.start_at
        end_at = data.end_at or booking.end_at
        self._validate_booking_dates(trip, start_at, end_at)
        booking = await self.bookings.update(booking, data)
        if booking.status == BookingStatus.CONFIRMED:
            await self._check_conflicts(booking.trip_id, booking, exclude_id=booking.id)
        return BookingResponse.model_validate(booking)

    async def confirm_booking(self, booking_id: UUID) -> BookingResponse:
        booking = _require_booking(await self.bookings.get_by_id(booking_id), booking_id)
        if booking.status not in (BookingStatus.EXTRACTED, BookingStatus.CONFLICT):
            raise AppError("VALIDATION_ERROR", "Only extracted bookings can be confirmed.")
        trip = _require_trip(await self.trips.get_by_id(booking.trip_id), booking.trip_id)
        self._validate_booking_dates(trip, booking.start_at, booking.end_at)
        booking.status = BookingStatus.CONFIRMED
        await self._check_conflicts(booking.trip_id, booking, exclude_id=booking.id)
        await self.session.flush()
        await self.session.refresh(booking)
        return BookingResponse.model_validate(booking)

    async def reject_booking(self, booking_id: UUID) -> BookingResponse:
        booking = _require_booking(await self.bookings.get_by_id(booking_id), booking_id)
        booking.status = BookingStatus.REJECTED
        await self.session.flush()
        await self.session.refresh(booking)
        return BookingResponse.model_validate(booking)
