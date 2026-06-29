from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.db.session import get_db
from app.schemas import BookingCreate, BookingUpdate
from app.services.trips import BookingService

router = APIRouter(tags=["bookings"])


@router.post("/trips/{trip_id}/bookings")
async def create_booking(
    trip_id: str, data: BookingCreate, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await BookingService(db).create_booking(trip_id, data)
    return success(result.model_dump())


@router.get("/trips/{trip_id}/bookings")
async def list_bookings(
    trip_id: str,
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    bookings = await BookingService(db).list_bookings(trip_id, status)
    return success([b.model_dump() for b in bookings])


@router.patch("/bookings/{booking_id}")
async def update_booking(
    booking_id: str, data: BookingUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await BookingService(db).update_booking(booking_id, data)
    return success(result.model_dump())


@router.post("/bookings/{booking_id}/confirm")
async def confirm_booking(booking_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await BookingService(db).confirm_booking(booking_id)
    return success(result.model_dump())


@router.post("/bookings/{booking_id}/reject")
async def reject_booking(booking_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await BookingService(db).reject_booking(booking_id)
    return success(result.model_dump())
