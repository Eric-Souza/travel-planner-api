from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


async def _create_trip(client: AsyncClient, name: str = "Test Trip") -> str:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 14, tzinfo=UTC)
    resp = await client.post(
        "/v1/trips",
        json={"name": name, "start_date": start.isoformat(), "end_date": end.isoformat()},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


@pytest.mark.asyncio
async def test_extract_confirm_booking_flow(client: AsyncClient) -> None:
    trip_id = await _create_trip(client, "Confirm Flow")

    upload = await client.post(
        f"/v1/trips/{trip_id}/documents",
        files={"file": ("hotel.txt", b"Reservation CONF999\nCheck-in 15:00", "text/plain")},
    )
    doc_id = upload.json()["data"]["id"]
    await client.post(f"/v1/documents/{doc_id}/process")
    extract = await client.post(f"/v1/documents/{doc_id}/extract-booking")
    booking_id = extract.json()["data"]["id"]
    assert extract.json()["data"]["status"] == "extracted"

    confirm = await client.post(f"/v1/bookings/{booking_id}/confirm")
    assert confirm.status_code == 200
    assert confirm.json()["data"]["status"] == "confirmed"

    listed = await client.get(f"/v1/trips/{trip_id}/bookings?status=confirmed")
    assert any(b["id"] == booking_id for b in listed.json()["data"])


@pytest.mark.asyncio
async def test_reject_extracted_booking(client: AsyncClient) -> None:
    trip_id = await _create_trip(client, "Reject Flow")
    upload = await client.post(
        f"/v1/trips/{trip_id}/documents",
        files={"file": ("note.txt", b"Restaurant booking 7pm", "text/plain")},
    )
    doc_id = upload.json()["data"]["id"]
    await client.post(f"/v1/documents/{doc_id}/process")
    extract = await client.post(f"/v1/documents/{doc_id}/extract-booking")
    booking_id = extract.json()["data"]["id"]

    reject = await client.post(f"/v1/bookings/{booking_id}/reject")
    assert reject.status_code == 200
    assert reject.json()["data"]["status"] == "rejected"


@pytest.mark.asyncio
async def test_preferences_update(client: AsyncClient) -> None:
    trip_id = await _create_trip(client, "Prefs Trip")

    get_resp = await client.get(f"/v1/trips/{trip_id}/preferences")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["trip_id"] == trip_id

    patch = await client.patch(
        f"/v1/trips/{trip_id}/preferences",
        json={
            "budget_level": "luxury",
            "pace": "relaxed",
            "hiking_interest": 5,
            "notes": "Prefer walkable neighborhoods",
        },
    )
    assert patch.status_code == 200
    data = patch.json()["data"]
    assert data["budget_level"] == "luxury"
    assert data["pace"] == "relaxed"
    assert data["hiking_interest"] == 5
    assert data["notes"] == "Prefer walkable neighborhoods"


@pytest.mark.asyncio
async def test_trip_not_found_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/v1/trips/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "request_id" in body


@pytest.mark.asyncio
async def test_unsupported_document_extension(client: AsyncClient) -> None:
    trip_id = await _create_trip(client, "Bad Upload")
    resp = await client.post(
        f"/v1/trips/{trip_id}/documents",
        files={"file": ("virus.exe", b"bad", "application/octet-stream")},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
