from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.db.session import get_db
from app.schemas import TripCreate, TripRead, TripSummary, TripUpdate
from app.services.trips import TripService

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("")
async def create_trip(data: TripCreate, db: AsyncSession = Depends(get_db)) -> dict:
    result = await TripService(db).create_trip(data)
    return success(result.model_dump())


@router.get("")
async def list_trips(db: AsyncSession = Depends(get_db)) -> dict:
    trips = await TripService(db).list_trips()
    return success([t.model_dump() for t in trips])


@router.get("/{trip_id}")
async def get_trip(trip_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await TripService(db).get_trip(trip_id)
    return success(result.model_dump())


@router.patch("/{trip_id}")
async def update_trip(trip_id: str, data: TripUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    result = await TripService(db).update_trip(trip_id, data)
    return success(result.model_dump())
