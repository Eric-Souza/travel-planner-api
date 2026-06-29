"""Seed synthetic Buenos Aires + Bariloche demo trip."""
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.db.init_db import init_db
from app.models import tables  # noqa: F401
from app.models.tables import Booking, TravelPreference, Trip
from app.schemas import BookingStatus

settings = get_settings()


async def seed() -> None:
    engine = create_async_engine(settings.database_url, connect_args={"check_same_thread": False})
    await init_db(engine)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        start = datetime(2026, 8, 1, tzinfo=UTC)
        end = datetime(2026, 8, 14, tzinfo=UTC)
        trip = Trip(
            name="Buenos Aires + Bariloche",
            start_date=start,
            end_date=end,
            base_currency="USD",
            home_timezone="America/Argentina/Buenos_Aires",
        )
        session.add(trip)
        await session.flush()
        pref = TravelPreference(
            trip_id=trip.id,
            budget_level="moderate",
            pace="moderate",
            interests="food, culture, hiking",
            food_preferences="steak, empanadas",
            hiking_interest=4,
        )
        session.add(pref)
        session.add(
            Booking(
                trip_id=trip.id,
                type="hotel",
                provider="Demo Hotels",
                title="Palermo Soho Hotel",
                confirmation_code="DEMO-BA-001",
                start_at=start + timedelta(days=1, hours=15),
                end_at=start + timedelta(days=4, hours=11),
                timezone="America/Argentina/Buenos_Aires",
                cost_amount=450.0,
                currency="USD",
                status=BookingStatus.CONFIRMED.value,
                location_name="Buenos Aires",
            )
        )
        session.add(
            Booking(
                trip_id=trip.id,
                type="flight",
                provider="Demo Air",
                title="Flight to Bariloche",
                confirmation_code="DEMO-FLT-002",
                start_at=start + timedelta(days=4, hours=10),
                end_at=start + timedelta(days=4, hours=12),
                timezone="America/Argentina/Buenos_Aires",
                status=BookingStatus.CONFIRMED.value,
            )
        )
        await session.commit()
        print(f"Seeded trip {trip.id}: Buenos Aires + Bariloche")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
