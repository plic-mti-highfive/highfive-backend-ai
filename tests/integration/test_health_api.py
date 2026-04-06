import pytest
from httpx import ASGITransport, AsyncClient

from src.server import create_app

app = create_app()


@pytest.mark.asyncio
async def test_livez():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/livez")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_readyz():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/readyz")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
        assert response.json()["database"] == "connected"


@pytest.mark.asyncio
async def test_healthz():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/healthz")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "components": {"api": "up", "database": "up"},
        }
