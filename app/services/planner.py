import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.tables import Booking, ItineraryItem, ItineraryProposal, ItineraryVersion
from app.schemas import (
    BookingStatus,
    ItineraryItemRead,
    ItineraryProposalCreate,
    ItineraryProposalItemSchema,
    ItineraryProposalRead,
    ItineraryVersionRead,
)
from app.services.tools.adapters import WeatherAdapter
from app.services.trips import TripService


class PlannerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.trips = TripService(session)
        self.weather = WeatherAdapter()

    async def generate_proposal(
        self, trip_id: str, data: ItineraryProposalCreate
    ) -> ItineraryProposalRead:
        trip = await self.trips._get_trip(trip_id)
        prefs = await self.trips.get_preferences(trip_id)
        confirmed = await self._confirmed_bookings(trip_id)
        before_items: list[ItineraryProposalItemSchema] | None = None
        warnings: list[str] = []

        current = await self.get_active_itinerary(trip_id)
        if data.mode == "rainy_day" and data.target_date:
            before_items = [
                ItineraryProposalItemSchema(
                    date=item.date.date().isoformat(),
                    start_time=item.start_time,
                    end_time=item.end_time,
                    title=item.title,
                    description=item.description,
                    is_confirmed=item.is_confirmed,
                    is_locked=item.is_locked,
                    is_outdoor=item.is_outdoor,
                    booking_id=item.booking_id,
                )
                for item in (current.items if current else [])
            ]
            weather = await self.weather.get_weather(-34.6037, -58.3816, data.target_date.date())
            if weather.condition == "rainy":
                warnings.append(f"Rain expected on {data.target_date.date()}")

        items: list[ItineraryProposalItemSchema] = []
        day = trip.start_date
        while day <= trip.end_date:
            day_items = self._day_skeleton(day, confirmed, prefs.pace)
            items.extend(day_items)
            day += timedelta(days=1)

        if data.mode == "rainy_day" and data.target_date:
            target_str = data.target_date.date().isoformat()
            for item in items:
                if item.date == target_str and item.is_outdoor and not item.is_locked:
                    item.title = f"Indoor alternative: {item.title}"
                    item.is_outdoor = False
                    item.warnings.append("Replaced due to rainy weather")

        items, overlap_warnings = self._validate_items(items, confirmed)
        warnings.extend(overlap_warnings)

        proposal = ItineraryProposal(
            trip_id=trip_id,
            status="pending",
            mode=data.mode,
            target_date=data.target_date,
            warnings_json=json.dumps(warnings),
            before_items_json=json.dumps([i.model_dump() for i in before_items]) if before_items else None,
            items_json=json.dumps([i.model_dump() for i in items]),
        )
        self.session.add(proposal)
        await self.session.flush()
        await self.session.refresh(proposal)
        return self._to_read(proposal)

    async def get_proposal(self, proposal_id: str) -> ItineraryProposalRead:
        proposal = await self._get_proposal(proposal_id)
        return self._to_read(proposal)

    async def apply_proposal(self, proposal_id: str) -> ItineraryVersionRead:
        proposal = await self._get_proposal(proposal_id)
        if proposal.status != "pending":
            raise ValidationError("Only pending proposals can be applied")
        items_data = json.loads(proposal.items_json or "[]")
        result = await self.session.execute(
            select(ItineraryVersion).where(
                ItineraryVersion.trip_id == proposal.trip_id,
                ItineraryVersion.is_active.is_(True),
            )
        )
        for v in result.scalars().all():
            v.is_active = False
        version_number = (
            await self.session.scalar(
                select(ItineraryVersion.version_number)
                .where(ItineraryVersion.trip_id == proposal.trip_id)
                .order_by(ItineraryVersion.version_number.desc())
                .limit(1)
            )
            or 0
        ) + 1
        version = ItineraryVersion(
            trip_id=proposal.trip_id,
            version_number=version_number,
            is_active=True,
        )
        self.session.add(version)
        await self.session.flush()
        for raw in items_data:
            item = ItineraryItem(
                itinerary_version_id=version.id,
                trip_id=proposal.trip_id,
                date=datetime.fromisoformat(raw["date"]).replace(tzinfo=UTC)
                if "T" not in raw["date"]
                else datetime.fromisoformat(raw["date"]),
                start_time=raw.get("start_time"),
                end_time=raw.get("end_time"),
                title=raw["title"],
                description=raw.get("description"),
                booking_id=raw.get("booking_id"),
                place_id=raw.get("place_id"),
                is_confirmed=raw.get("is_confirmed", False),
                is_locked=raw.get("is_locked", False),
                is_outdoor=raw.get("is_outdoor", False),
                warnings=json.dumps(raw.get("warnings", [])),
            )
            self.session.add(item)
        proposal.status = "applied"
        await self.session.flush()
        return await self.get_active_itinerary(proposal.trip_id)  # type: ignore[return-value]

    async def get_active_itinerary(self, trip_id: str) -> ItineraryVersionRead | None:
        await self.trips._get_trip(trip_id)
        result = await self.session.execute(
            select(ItineraryVersion).where(
                ItineraryVersion.trip_id == trip_id,
                ItineraryVersion.is_active.is_(True),
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            return None
        items_result = await self.session.execute(
            select(ItineraryItem).where(ItineraryItem.itinerary_version_id == version.id)
        )
        items = [ItineraryItemRead.model_validate(i) for i in items_result.scalars().all()]
        return ItineraryVersionRead(
            id=version.id,
            trip_id=version.trip_id,
            version_number=version.version_number,
            is_active=version.is_active,
            items=items,
            created_at=version.created_at,
            updated_at=version.updated_at,
        )

    async def _confirmed_bookings(self, trip_id: str) -> list[Booking]:
        result = await self.session.execute(
            select(Booking).where(
                Booking.trip_id == trip_id,
                Booking.status == BookingStatus.CONFIRMED.value,
            )
        )
        return list(result.scalars().all())

    def _day_skeleton(
        self, day: datetime, confirmed: list[Booking], pace: str
    ) -> list[ItineraryProposalItemSchema]:
        items: list[ItineraryProposalItemSchema] = []
        day_date = day.date() if hasattr(day, "date") else day
        day_str = day_date.isoformat() if hasattr(day_date, "isoformat") else str(day_date)[:10]
        for b in confirmed:
            if b.start_at.date().isoformat() == day_str:
                items.append(
                    ItineraryProposalItemSchema(
                        date=day_str,
                        start_time=b.start_at.strftime("%H:%M"),
                        end_time=b.end_at.strftime("%H:%M"),
                        title=b.title,
                        description=f"Confirmed {b.type}",
                        is_confirmed=True,
                        is_locked=True,
                        booking_id=b.id,
                    )
                )
        if pace != "relaxed" and not any(i.is_confirmed for i in items):
            items.append(
                ItineraryProposalItemSchema(
                    date=day_str,
                    start_time="10:00",
                    end_time="12:00",
                    title="Explore neighborhood",
                    description="Suggested walking tour",
                    is_outdoor=True,
                )
            )
        return items

    def _validate_items(
        self, items: list[ItineraryProposalItemSchema], confirmed: list[Booking]
    ) -> tuple[list[ItineraryProposalItemSchema], list[str]]:
        warnings: list[str] = []
        locked_ids = {b.id for b in confirmed}
        for item in items:
            if item.booking_id and item.booking_id not in locked_ids and item.is_locked:
                warnings.append(f"Locked item missing booking: {item.title}")
        return items, warnings

    async def _get_proposal(self, proposal_id: str) -> ItineraryProposal:
        result = await self.session.execute(
            select(ItineraryProposal).where(ItineraryProposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        if not proposal:
            raise NotFoundError("ItineraryProposal", proposal_id)
        return proposal

    def _to_read(self, proposal: ItineraryProposal) -> ItineraryProposalRead:
        items = [
            ItineraryProposalItemSchema.model_validate(i)
            for i in json.loads(proposal.items_json or "[]")
        ]
        before = (
            [ItineraryProposalItemSchema.model_validate(i) for i in json.loads(proposal.before_items_json)]
            if proposal.before_items_json
            else None
        )
        return ItineraryProposalRead(
            id=proposal.id,
            trip_id=proposal.trip_id,
            status=proposal.status,
            mode=proposal.mode,
            target_date=proposal.target_date,
            items=items,
            warnings=json.loads(proposal.warnings_json or "[]"),
            before_items=before,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
        )
