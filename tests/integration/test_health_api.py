"""Endpoints système : livez, readyz, status, workers-status (Postgres + Redis réels)."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.v1 import health
from src.infrastructure.database import get_db
from src.server import create_app


@pytest.fixture()
def app():
    app = create_app()
    yield app
    app.dependency_overrides.clear()


@pytest.fixture()
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c


class BrokenDb:
    async def execute(self, *a, **k):
        raise ConnectionError("db down")


def break_db(app):
    async def _broken():
        yield BrokenDb()

    app.dependency_overrides[get_db] = _broken


async def test_livez(client):
    r = await client.get("/api/v1/livez")
    assert r.status_code == 200 and r.json() == {"status": "alive"}


async def test_readyz_ok(client):
    r = await client.get("/api/v1/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "database": "connected"}


async def test_readyz_db_down_is_503(app, client):
    break_db(app)
    r = await client.get("/api/v1/readyz")
    assert r.status_code == 503
    assert r.json()["detail"]["database"] == "disconnected"


async def test_status_all_up(client):
    r = await client.get("/api/v1/status")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "components": {"api": "up", "database": "up", "redis": "up", "workers": "up"},
    }


async def test_status_degraded_when_redis_down_is_200(client, monkeypatch):
    monkeypatch.setitem(health.settings.__dict__, "REDIS_PORT", 1)  # port fermé
    r = await client.get("/api/v1/status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["components"]["database"] == "up"
    assert body["components"]["redis"] == "down"


async def test_status_degraded_when_workers_unhealthy(client, monkeypatch):
    async def unhealthy(self, queues):
        return False

    monkeypatch.setattr(health.WorkerMonitor, "are_workers_healthy", unhealthy)
    r = await client.get("/api/v1/status")
    assert r.status_code == 200
    assert r.json()["components"]["workers"] == "degraded"
    assert r.json()["status"] == "degraded"


async def test_status_unavailable_when_db_down_is_503(app, client):
    break_db(app)
    r = await client.get("/api/v1/status")
    assert r.status_code == 503
    assert r.json()["detail"]["status"] == "unavailable"
    assert r.json()["detail"]["components"]["database"] == "down"


async def test_workers_status_lists_contract_queues(client):
    r = await client.get("/api/v1/workers-status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body["queues"]) == {"ai_tasks", "fast_events"}


async def test_chat_generate_requires_auth(client):
    assert (await client.post("/api/v1/chat/generate", json={"prompt": "idée"})).status_code in (
        401,
        403,
    )


async def test_chat_generate_replies_and_validates_prompt(client, auth_headers):
    r = await client.post("/api/v1/chat/generate", json={"prompt": "un jeu"}, headers=auth_headers)
    assert r.status_code == 200
    assert "un jeu" in r.json()["reply"]
    r = await client.post("/api/v1/chat/generate", json={"prompt": "x"}, headers=auth_headers)
    assert r.status_code == 422
