from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.db.session import get_db
from app.schemas import PlaceCreate, PlaceSearchRequest
from app.services.places import PlaceService

router = APIRouter(prefix="/trips/{trip_id}/places", tags=["places"])


@router.get("")
async def list_places(trip_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    places = await PlaceService(db).list_places(trip_id)
    return success([p.model_dump() for p in places])


@router.post("")
async def create_place(
    trip_id: str, data: PlaceCreate, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await PlaceService(db).create_place(trip_id, data)
    return success(result.model_dump())


@router.delete("/{place_id}")
async def delete_place(
    trip_id: str, place_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    await PlaceService(db).delete_place(place_id)
    return success({"deleted": place_id})


@router.post("/search")
async def search_places(
    trip_id: str, data: PlaceSearchRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    results = await PlaceService(db).search(trip_id, data)
    return success([r.model_dump() for r in results])
