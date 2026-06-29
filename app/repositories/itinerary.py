from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    Conversation,
    ItineraryItem,
    ItineraryProposal,
    ItineraryProposalItem,
    ItineraryVersion,
    Message,
    Place,
)
from app.models.enums import ItineraryItemStatus, ProposalStatus


class ItineraryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_version(self, trip_id: UUID) -> ItineraryVersion | None:
        result = await self.session.execute(
            select(ItineraryVersion).where(
                ItineraryVersion.trip_id == trip_id, ItineraryVersion.is_active.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def create_version(self, trip_id: UUID, version_number: int) -> ItineraryVersion:
        result = await self.session.execute(
            select(ItineraryVersion).where(ItineraryVersion.trip_id == trip_id)
        )
        for v in result.scalars().all():
            v.is_active = False
        version = ItineraryVersion(trip_id=trip_id, version_number=version_number, is_active=True)
        self.session.add(version)
        await self.session.flush()
        await self.session.refresh(version)
        return version

    async def add_items(self, items: list[ItineraryItem]) -> None:
        self.session.add_all(items)
        await self.session.flush()

    async def get_items_for_version(self, version_id: UUID) -> list[ItineraryItem]:
        result = await self.session.execute(
            select(ItineraryItem).where(ItineraryItem.version_id == version_id)
        )
        return list(result.scalars().all())

    async def create_proposal(self, proposal: ItineraryProposal) -> ItineraryProposal:
        self.session.add(proposal)
        await self.session.flush()
        await self.session.refresh(proposal)
        return proposal

    async def get_proposal(self, proposal_id: UUID) -> ItineraryProposal | None:
        result = await self.session.execute(
            select(ItineraryProposal).where(ItineraryProposal.id == proposal_id)
        )
        return result.scalar_one_or_none()

    async def add_proposal_items(self, items: list[ItineraryProposalItem]) -> None:
        self.session.add_all(items)
        await self.session.flush()


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, trip_id: UUID, title: str | None = None) -> Conversation:
        conv = Conversation(trip_id=trip_id, title=title)
        self.session.add(conv)
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_by_trip(self, trip_id: UUID) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(Conversation.trip_id == trip_id).order_by(
                Conversation.updated_at.desc()
            )
        )
        return list(result.scalars().all())

    async def add_message(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def get_messages(self, conversation_id: UUID) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())


class PlaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, place: Place) -> Place:
        self.session.add(place)
        await self.session.flush()
        await self.session.refresh(place)
        return place

    async def list_by_trip(self, trip_id: UUID) -> list[Place]:
        result = await self.session.execute(
            select(Place).where(Place.trip_id == trip_id).order_by(Place.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, place_id: UUID) -> Place | None:
        result = await self.session.execute(select(Place).where(Place.id == place_id))
        return result.scalar_one_or_none()

    async def delete(self, place: Place) -> None:
        await self.session.delete(place)
        await self.session.flush()
