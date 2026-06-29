from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_stream_returns_sse_events(client: AsyncClient) -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 14, tzinfo=UTC)
    trip_id = (
        await client.post(
            "/v1/trips",
            json={"name": "Chat Trip", "start_date": start.isoformat(), "end_date": end.isoformat()},
        )
    ).json()["data"]["id"]

    response = await client.post(
        f"/v1/trips/{trip_id}/chat/stream",
        json={"message": "What is booked for Tuesday?"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = response.text
    assert "event:" in body
    assert "data:" in body
    assert "token" in body or "done" in body or "status" in body


@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient) -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 14, tzinfo=UTC)
    trip_id = (
        await client.post(
            "/v1/trips",
            json={"name": "Conv Trip", "start_date": start.isoformat(), "end_date": end.isoformat()},
        )
    ).json()["data"]["id"]

    resp = await client.get(f"/v1/trips/{trip_id}/conversations")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
