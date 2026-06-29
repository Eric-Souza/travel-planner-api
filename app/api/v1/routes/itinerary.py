from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.db.session import get_db
from app.schemas import ItineraryProposalCreate
from app.services.planner import PlannerService

router = APIRouter(tags=["itinerary"])


@router.post("/trips/{trip_id}/itinerary-proposals")
async def create_proposal(
    trip_id: str, data: ItineraryProposalCreate, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await PlannerService(db).generate_proposal(trip_id, data)
    return success(result.model_dump())


@router.get("/itinerary-proposals/{proposal_id}")
async def get_proposal(proposal_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await PlannerService(db).get_proposal(proposal_id)
    return success(result.model_dump())


@router.post("/itinerary-proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await PlannerService(db).apply_proposal(proposal_id)
    return success(result.model_dump())


@router.get("/trips/{trip_id}/itineraries")
async def get_itinerary(trip_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await PlannerService(db).get_active_itinerary(trip_id)
    return success(result.model_dump() if result else None)
