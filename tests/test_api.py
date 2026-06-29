from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert "request_id" in body


@pytest.mark.asyncio
async def test_v1_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_create_trip_and_booking(client: AsyncClient) -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 14, tzinfo=UTC)
    trip_resp = await client.post(
        "/v1/trips",
        json={
            "name": "Buenos Aires + Bariloche",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "base_currency": "USD",
            "home_timezone": "America/Argentina/Buenos_Aires",
        },
    )
    assert trip_resp.status_code == 200
    trip_id = trip_resp.json()["data"]["id"]

    booking_resp = await client.post(
        f"/v1/trips/{trip_id}/bookings",
        json={
            "type": "hotel",
            "title": "Palermo Hotel",
            "start_at": (start + timedelta(days=1)).isoformat(),
            "end_at": (start + timedelta(days=3)).isoformat(),
            "timezone": "America/Argentina/Buenos_Aires",
            "status": "confirmed",
        },
    )
    assert booking_resp.status_code == 200
    assert booking_resp.json()["data"]["title"] == "Palermo Hotel"

    list_resp = await client.get(f"/v1/trips/{trip_id}/bookings")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 1


@pytest.mark.asyncio
async def test_booking_validation_end_before_start(client: AsyncClient) -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 14, tzinfo=UTC)
    trip_resp = await client.post(
        "/v1/trips",
        json={
            "name": "Test Trip",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
    )
    trip_id = trip_resp.json()["data"]["id"]
    bad = await client.post(
        f"/v1/trips/{trip_id}/bookings",
        json={
            "type": "flight",
            "title": "Invalid",
            "start_at": end.isoformat(),
            "end_at": start.isoformat(),
        },
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_document_upload_and_parse(client: AsyncClient) -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 14, tzinfo=UTC)
    trip_id = (
        await client.post(
            "/v1/trips",
            json={"name": "Doc Trip", "start_date": start.isoformat(), "end_date": end.isoformat()},
        )
    ).json()["data"]["id"]

    content = b"HOTEL RESERVATION\nCheck-in: 15:00\nConfirmation: ABC123"
    upload = await client.post(
        f"/v1/trips/{trip_id}/documents",
        files={"file": ("hotel.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    doc_id = upload.json()["data"]["id"]

    processed = await client.post(f"/v1/documents/{doc_id}/process")
    assert processed.status_code == 200
    assert processed.json()["data"]["processing_status"] == "parsed"

    extracted = await client.post(f"/v1/documents/{doc_id}/extract-booking")
    assert extracted.status_code == 200
    assert extracted.json()["data"]["status"] == "extracted"

    candidate = await client.get(f"/v1/documents/{doc_id}/booking-candidate")
    assert candidate.status_code == 200
    assert candidate.json()["data"]["extraction"] is not None
