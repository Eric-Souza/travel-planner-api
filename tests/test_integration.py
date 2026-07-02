from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_live_health_endpoint() -> None:
    """Smoke test against a running uvicorn instance (skipped if server is down)."""
    import httpx

    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=2.0) as client:
            response = await client.get("/health")
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
        pytest.skip("API server not running on http://127.0.0.1:8000")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_places_create_and_list(client: AsyncClient) -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 14, tzinfo=UTC)
    trip_id = (
        await client.post(
            "/v1/trips",
            json={"name": "Places Trip", "start_date": start.isoformat(), "end_date": end.isoformat()},
        )
    ).json()["data"]["id"]

    created = await client.post(
        f"/v1/trips/{trip_id}/places",
        json={
            "name": "Teatro Colon",
            "category": "attraction",
            "latitude": -34.6011,
            "longitude": -58.3832,
            "address": "Buenos Aires",
        },
    )
    assert created.status_code == 200
    assert created.json()["data"]["name"] == "Teatro Colon"

    listed = await client.get(f"/v1/trips/{trip_id}/places")
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1


@pytest.mark.asyncio
async def test_trip_update(client: AsyncClient) -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 14, tzinfo=UTC)
    trip_id = (
        await client.post(
            "/v1/trips",
            json={"name": "Original", "start_date": start.isoformat(), "end_date": end.isoformat()},
        )
    ).json()["data"]["id"]

    updated = await client.patch(
        f"/v1/trips/{trip_id}",
        json={"name": "Updated Trip Name"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "Updated Trip Name"

    fetched = await client.get(f"/v1/trips/{trip_id}")
    assert fetched.json()["data"]["name"] == "Updated Trip Name"
