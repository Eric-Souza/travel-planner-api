from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_itinerary_proposal_and_apply(client: AsyncClient) -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 5, tzinfo=UTC)
    trip_id = (
        await client.post(
            "/v1/trips",
            json={"name": "Planner Trip", "start_date": start.isoformat(), "end_date": end.isoformat()},
        )
    ).json()["data"]["id"]

    await client.post(
        f"/v1/trips/{trip_id}/bookings",
        json={
            "type": "hotel",
            "title": "Locked Hotel",
            "start_at": (start + timedelta(days=1)).isoformat(),
            "end_at": (start + timedelta(days=2)).isoformat(),
            "status": "confirmed",
        },
    )

    proposal = await client.post(
        f"/v1/trips/{trip_id}/itinerary-proposals",
        json={"mode": "standard"},
    )
    assert proposal.status_code == 200
    proposal_id = proposal.json()["data"]["id"]
    items = proposal.json()["data"]["items"]
    assert any(i["is_locked"] for i in items)

    applied = await client.post(f"/v1/itinerary-proposals/{proposal_id}/apply")
    assert applied.status_code == 200
    itinerary = await client.get(f"/v1/trips/{trip_id}/itineraries")
    assert itinerary.status_code == 200
    assert itinerary.json()["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_document_search_and_ask(client: AsyncClient) -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 14, tzinfo=UTC)
    trip_id = (
        await client.post(
            "/v1/trips",
            json={"name": "RAG Trip", "start_date": start.isoformat(), "end_date": end.isoformat()},
        )
    ).json()["data"]["id"]

    content = b"CANCELLATION POLICY\nFree cancellation until 48 hours before check-in.\nCheck-in begins at 15:00."
    upload = await client.post(
        f"/v1/trips/{trip_id}/documents",
        files={"file": ("policy.txt", content, "text/plain")},
    )
    doc_id = upload.json()["data"]["id"]
    await client.post(f"/v1/documents/{doc_id}/process")
    await client.post(f"/v1/documents/{doc_id}/embed")

    search = await client.post(
        f"/v1/trips/{trip_id}/search",
        json={"query": "cancellation policy"},
    )
    assert search.status_code == 200
    assert len(search.json()["data"]["chunks"]) >= 1

    ask = await client.post(
        f"/v1/trips/{trip_id}/ask-document-question",
        json={"question": "What is the cancellation policy?"},
    )
    assert ask.status_code == 200
    assert ask.json()["data"]["answer"]


@pytest.mark.asyncio
async def test_eval_endpoint(client: AsyncClient) -> None:
    response = await client.post("/v1/eval/run")
    assert response.status_code == 200
    assert response.json()["data"]["extraction_valid"] is True
