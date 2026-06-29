import hashlib
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.llm.provider import ChatResult, LLMProvider, StreamEvent

logger = logging.getLogger(__name__)
settings = get_settings()


def _mock_embedding(text: str, dim: int = 384) -> list[float]:
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
        yield StreamEvent(type="done", data={"usage": {"input_chars": len(last), "output_chars": len(text)}})

    async def structured_output(
        self, messages: list[dict[str, str]], schema: type[BaseModel]
    ) -> BaseModel:
        name = schema.__name__
        if name == "DocumentClassification":
            from app.schemas import DocumentClassification, DocumentType

            return DocumentClassification(document_type=DocumentType.HOTEL_RESERVATION, confidence=0.85)
        if name == "BookingExtraction":
            from app.schemas import BookingEvidence, BookingExtraction

            start_at = datetime(2026, 8, 5, 15, 0, tzinfo=timezone.utc)
            end_at = datetime(2026, 8, 8, 11, 0, tzinfo=timezone.utc)
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
        return [_mock_embedding(t) for t in texts]


class OllamaProvider:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.chat_model = settings.ollama_chat_model
        self.embedding_model = settings.ollama_embedding_model

    async def _available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def chat(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> ChatResult:
        if not await self._available():
            return await MockLLMProvider().chat(messages, tools)
        payload: dict[str, Any] = {"model": self.chat_model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
            return ChatResult(content=data.get("message", {}).get("content", ""))

    async def stream_chat(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[StreamEvent]:
        if not await self._available():
            async for ev in MockLLMProvider().stream_chat(messages, tools):
                yield ev
            return
        payload = {"model": self.chat_model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield StreamEvent(type="token", data={"text": content})
                    if data.get("done"):
                        yield StreamEvent(
                            type="done",
                            data={"usage": {"input_chars": 0, "output_chars": len(content)}},
                        )

    async def structured_output(
        self, messages: list[dict[str, str]], schema: type[BaseModel]
    ) -> BaseModel:
        if not await self._available():
            return await MockLLMProvider().structured_output(messages, schema)
        schema_json = schema.model_json_schema()
        prompt = messages + [
            {
                "role": "user",
                "content": f"Return ONLY valid JSON matching this schema:\n{json.dumps(schema_json)}",
            }
        ]
        result = await self.chat(prompt)
        try:
            parsed = json.loads(result.content)
            return schema.model_validate(parsed)
        except Exception:
            logger.warning("Ollama structured output failed, using mock")
            return await MockLLMProvider().structured_output(messages, schema)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not await self._available():
            return await MockLLMProvider().embed(texts)
        vectors: list[list[float]] = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                r = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                )
                if r.status_code != 200:
                    vectors.append(_mock_embedding(text))
                else:
                    vectors.append(r.json().get("embedding", _mock_embedding(text)))
        return vectors


def get_llm_provider() -> LLMProvider:
    if settings.use_mock_llm:
        return MockLLMProvider()
    return OllamaProvider()
