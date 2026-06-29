import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert "request_id" in body
    assert response.headers.get("X-Request-ID")


@pytest.mark.asyncio
async def test_v1_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
