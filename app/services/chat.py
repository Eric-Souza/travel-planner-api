import json
import re
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_id import get_request_id
from app.models.tables import AuditLog, Booking, Message, ToolRun
from app.schemas import BookingStatus, SourceCitation
from app.services.llm.ollama import get_llm_provider
from app.services.retrieval import RetrievalService
from app.services.tools.adapters import CurrencyAdapter, PlacesAdapter, RoutingAdapter, WeatherAdapter
from app.services.trips import TripService


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.llm = get_llm_provider()
        self.trips = TripService(session)
        self.retrieval = RetrievalService(session)
        self.weather = WeatherAdapter()
        self.currency = CurrencyAdapter()
        self.places = PlacesAdapter()
        self.routing = RoutingAdapter()

    async def stream_answer(self, trip_id: str, question: str, conversation_id: str) -> AsyncIterator[dict]:
        trip = await self.trips._get_trip(trip_id)
        yield {"event": "status", "data": {"message": "Analyzing your question"}}

        q_lower = question.lower()
        sources: list[SourceCitation] = []
        tool_results: list[dict] = []

        if self._is_booking_question(q_lower):
            yield {"event": "status", "data": {"message": "Searching confirmed bookings"}}
            target_date = self._resolve_date(question, trip.home_timezone)
            bookings = await self._bookings_for_date(trip_id, target_date)
            context = self._format_bookings(bookings)
            for b in bookings:
                sources.append(
                    SourceCitation(
                        type="booking",
                        title=b.title,
                        excerpt=f"{b.type} {b.start_at.isoformat()} - {b.end_at.isoformat()}",
                        source_id=b.id,
                    )
                )
            prompt = f"Answer based on confirmed bookings only:\n{context}\n\nQuestion: {question}"
        elif self._is_policy_question(q_lower):
            yield {"event": "status", "data": {"message": "Searching trip documents"}}
            from app.schemas import AskDocumentQuestionRequest

            answer = await self.retrieval.ask(trip_id, AskDocumentQuestionRequest(question=question))
            sources = answer.sources
            if not answer.found:
                yield {"event": "sources", "data": {"sources": []}}
                yield {"event": "token", "data": {"text": answer.answer}}
                yield {"event": "done", "data": {"message_id": "", "sources": []}}
                return
            prompt = f"Question: {question}\n\nSources:\n" + "\n".join(s.excerpt for s in sources)
        elif "weather" in q_lower:
            yield {"event": "status", "data": {"message": "Checking weather"}}
            target = date.today()
            lat, lon = -34.6037, -58.3816
            weather = await self.weather.get_weather(lat, lon, target)
            tool_results.append(weather.model_dump())
            yield {"event": "tool_result", "data": {"tool": "get_weather", "result": weather.model_dump()}}
            prompt = f"Weather data: {weather.model_dump()}\n\nQuestion: {question}"
        elif "exchange" in q_lower or "currency" in q_lower:
            yield {"event": "status", "data": {"message": "Checking exchange rate"}}
            rate = await self.currency.get_exchange_rate(trip.base_currency, "EUR", date.today())
            tool_results.append(rate.model_dump())
            yield {"event": "tool_result", "data": {"tool": "get_exchange_rate", "result": rate.model_dump()}}
            prompt = f"Rate: {rate.model_dump()}\n\nQuestion: {question}"
        else:
            yield {"event": "status", "data": {"message": "Searching trip documents"}}
            from app.schemas import AskDocumentQuestionRequest

            answer = await self.retrieval.ask(trip_id, AskDocumentQuestionRequest(question=question))
            sources = answer.sources
            prompt = answer.answer if not answer.found else f"Summarize: {question}\n{answer.answer}"

        if sources:
            yield {"event": "sources", "data": {"sources": [s.model_dump(mode="json") for s in sources]}}

        full_text = ""
        async for event in self.llm.stream_chat([{"role": "user", "content": prompt}]):
            if event.type == "token":
                text = event.data.get("text", "")
                full_text += text
                yield {"event": "token", "data": {"text": text}}

        msg = Message(
            conversation_id=conversation_id,
            trip_id=trip_id,
            role="assistant",
            content=full_text,
            sources_json=json.dumps([s.model_dump(mode="json") for s in sources]),
        )
        self.session.add(msg)
        await self.session.flush()
        await self.session.refresh(msg)
        yield {
            "event": "done",
            "data": {
                "message_id": msg.id,
                "sources": [s.model_dump(mode="json") for s in sources],
                "usage": {"output_chars": len(full_text)},
            },
        }

    async def _bookings_for_date(self, trip_id: str, target: date | None) -> list[Booking]:
        result = await self.session.execute(
            select(Booking).where(
                Booking.trip_id == trip_id,
                Booking.status == BookingStatus.CONFIRMED.value,
            )
        )
        bookings = list(result.scalars().all())
        if not target:
            return bookings
        return [b for b in bookings if b.start_at.date() <= target <= b.end_at.date()]

    def _format_bookings(self, bookings: list[Booking]) -> str:
        return "\n".join(
            f"- {b.title} ({b.type}): {b.start_at.isoformat()} to {b.end_at.isoformat()}"
            for b in bookings
        )

    def _is_booking_question(self, q: str) -> bool:
        return any(w in q for w in ("booked", "booking", "reservation", "schedule", "tuesday", "wednesday"))

    def _is_policy_question(self, q: str) -> bool:
        return any(w in q for w in ("policy", "cancellation", "check-in", "check in", "luggage"))

    def _resolve_date(self, question: str, _tz: str) -> date | None:
        days = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        q = question.lower()
        for name, _ in days.items():
            if name in q:
                today = datetime.now(UTC).date()
                return today
        return None


async def log_tool_run(
    session: AsyncSession,
    tool_name: str,
    arguments: dict,
    result: dict,
    cache_hit: bool = False,
    duration_ms: int = 0,
    trip_id: str | None = None,
) -> None:
    session.add(
        ToolRun(
            request_id=get_request_id(),
            trip_id=trip_id,
            tool_name=tool_name,
            arguments_json=json.dumps(arguments),
            result_summary=result.get("summary", tool_name),
            result_json=json.dumps(result),
            cache_hit=cache_hit,
            duration_ms=duration_ms,
        )
    )


async def log_audit(
    session: AsyncSession,
    event_type: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    trip_id: str | None = None,
    details: dict | None = None,
    model_name: str | None = None,
    latency_ms: int | None = None,
) -> None:
    session.add(
        AuditLog(
            request_id=get_request_id(),
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            trip_id=trip_id,
            details_json=json.dumps(details or {}),
            model_name=model_name,
            latency_ms=latency_ms,
        )
    )
