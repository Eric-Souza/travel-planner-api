import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from app.services.llm.provider import ChatResult, StreamEvent


def mock_embedding(text: str, dim: int = 384) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    return [((digest[i % len(digest)] / 255.0) * 2 - 1) for i in range(dim)]


class MockLLMProvider:
    async def chat(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> ChatResult:
        last = messages[-1]["content"] if messages else ""
        return ChatResult(content=f"[mock] Response to: {last[:200]}")

    async def stream_chat(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[StreamEvent]:
        last = messages[-1]["content"] if messages else ""
        text = f"Based on your trip data: {last[:100]}"
        for word in text.split():
            yield StreamEvent(type="token", data={"text": word + " "})
        yield StreamEvent(
            type="done",
            data={"usage": {"input_chars": len(last), "output_chars": len(text)}},
        )

    async def structured_output(
        self, messages: list[dict[str, str]], schema: type[BaseModel]
    ) -> BaseModel:
        name = schema.__name__
        if name == "DocumentClassification":
            from app.schemas import DocumentClassification, DocumentType

            return DocumentClassification(
                document_type=DocumentType.HOTEL_RESERVATION, confidence=0.85
            )
        if name == "BookingExtraction":
            from app.schemas import BookingEvidence, BookingExtraction

            start_at = datetime(2026, 8, 5, 15, 0, tzinfo=UTC)
            end_at = datetime(2026, 8, 8, 11, 0, tzinfo=UTC)
            return BookingExtraction(
                type="hotel",
                provider="Mock Hotels",
                title="Mock Hotel Reservation",
                confirmation_code="MOCK123",
                start_at=start_at,
                end_at=end_at,
                timezone="America/Argentina/Buenos_Aires",
                location_name="Buenos Aires",
                total_amount=150.0,
                currency="USD",
                source_evidence=[BookingEvidence(excerpt="Check-in at 15:00", page=1)],
                confidence=0.8,
                uncertainty_notes=["Mock extraction - verify dates"],
            )
        return schema.model_validate({})

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [mock_embedding(t) for t in texts]
