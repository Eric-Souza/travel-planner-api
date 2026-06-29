from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.tables import Conversation, Message, Place
from app.schemas import (
    ConversationRead,
    MessageRead,
    PlaceCreate,
    PlaceRead,
    PlaceSearchRequest,
    PlaceSearchResult,
    SourceCitation,
)
from app.services.tools.adapters import PlacesAdapter
from app.services.trips import TripService


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, trip_id: str, conversation_id: str | None) -> Conversation:
        if conversation_id:
            result = await self.session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if conv:
                return conv
        conv = Conversation(trip_id=trip_id, title="Trip chat")
        self.session.add(conv)
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def list_conversations(self, trip_id: str) -> list[ConversationRead]:
        await TripService(self.session)._get_trip(trip_id)
        result = await self.session.execute(
            select(Conversation).where(Conversation.trip_id == trip_id).order_by(Conversation.updated_at.desc())
        )
        return [ConversationRead.model_validate(c) for c in result.scalars().all()]

    async def list_messages(self, conversation_id: str) -> list[MessageRead]:
        result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
        )
        messages: list[MessageRead] = []
        for m in result.scalars().all():
            import json

            sources = []
            if m.sources_json:
                sources = [SourceCitation.model_validate(s) for s in json.loads(m.sources_json)]
            msg = MessageRead.model_validate(m)
            msg.sources = sources
            messages.append(msg)
        return messages

    async def add_user_message(self, conversation_id: str, trip_id: str, content: str) -> Message:
        msg = Message(conversation_id=conversation_id, trip_id=trip_id, role="user", content=content)
        self.session.add(msg)
        await self.session.flush()
        return msg


class PlaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.adapter = PlacesAdapter()

    async def list_places(self, trip_id: str) -> list[PlaceRead]:
        await TripService(self.session)._get_trip(trip_id)
        result = await self.session.execute(select(Place).where(Place.trip_id == trip_id))
        return [PlaceRead.model_validate(p) for p in result.scalars().all()]

    async def create_place(self, trip_id: str, data: PlaceCreate) -> PlaceRead:
        await TripService(self.session)._get_trip(trip_id)
        place = Place(
            trip_id=trip_id,
            name=data.name,
            category=data.category,
            latitude=data.latitude,
            longitude=data.longitude,
            address=data.address,
            user_saved=data.user_saved,
        )
        self.session.add(place)
        await self.session.flush()
        await self.session.refresh(place)
        return PlaceRead.model_validate(place)

    async def delete_place(self, place_id: str) -> None:
        result = await self.session.execute(select(Place).where(Place.id == place_id))
        place = result.scalar_one_or_none()
        if not place:
            raise NotFoundError("Place", place_id)
        await self.session.delete(place)

    async def search(self, trip_id: str, request: PlaceSearchRequest) -> list[PlaceSearchResult]:
        await TripService(self.session)._get_trip(trip_id)
        results = await self.adapter.search_places(
            request.query, request.latitude, request.longitude, request.category
        )
        return [PlaceSearchResult(**r, source="nominatim") for r in results]
