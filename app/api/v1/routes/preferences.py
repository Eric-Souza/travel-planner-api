from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.db.session import get_db
from app.schemas import PreferenceRead, PreferenceUpdate
from app.services.trips import TripService

router = APIRouter(prefix="/trips/{trip_id}/preferences", tags=["preferences"])


@router.get("")
async def get_preferences(trip_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await TripService(db).get_preferences(trip_id)
    return success(result.model_dump())


@router.patch("")
async def update_preferences(
    trip_id: str, data: PreferenceUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await TripService(db).update_preferences(trip_id, data)
    return success(result.model_dump())
