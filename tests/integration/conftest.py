"""
Integration test fixtures - separate from unit tests.
Integration tests need real DB persists to work with AsyncClient.
"""

import pytest_asyncio
from sqlalchemy import text

from tests.conftest import TestingSessionLocal


@pytest_asyncio.fixture()
async def db_session(test_tenant_id):
    """
    DB session for integration tests.
    Data persists in DB (needed for AsyncClient to see it).
    Cleanup by tenant_id after test completes.
    """
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            # Clean up test data by tenant_id
            await session.execute(
                text("DELETE FROM embeddings WHERE tenant_id = :tenant_id"),
                {"tenant_id": test_tenant_id},
            )
            await session.commit()


# --- Fixtures partagées API / file Redis ---

import uuid  # noqa: E402

import jwt  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from scripts.fake_provider import FakeLLMProvider  # noqa: E402
from src.core.config import settings  # noqa: E402
from src.server import create_app  # noqa: E402
from src.worker.handlers import handle_project_identity, handle_user_identity  # noqa: E402


def make_token(tenant_id, user_id=None, **extra) -> str:
    payload = {"sub": str(user_id or uuid.uuid4()), "tenantId": str(tenant_id), **extra}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


@pytest.fixture()
def fake_provider():
    return FakeLLMProvider()


@pytest.fixture()
def auth_headers(test_tenant_id):
    return {"Authorization": f"Bearer {make_token(test_tenant_id)}"}


@pytest_asyncio.fixture()
async def client():
    """Client HTTP sur l'application complète, SANS override d'authentification."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c


@pytest_asyncio.fixture()
async def seeder(test_tenant_id, fake_provider):
    """Insère (commit réel) des utilisateurs/projets via les vrais handlers, provider factice."""

    class Seeder:
        tenant_id = test_tenant_id

        async def user(self, bio, skills=()):
            uid = uuid.uuid4()
            async with TestingSessionLocal() as s:
                await handle_user_identity(
                    {
                        "tenant_id": str(test_tenant_id),
                        "user_id": str(uid),
                        "payload": {"bio": bio, "skills": list(skills)},
                    },
                    s,
                    fake_provider,
                )
                await s.commit()
            return uid

        async def project(self, name, description, tags=(), visibility="PUBLIC"):
            pid = uuid.uuid4()
            async with TestingSessionLocal() as s:
                await handle_project_identity(
                    {
                        "tenant_id": str(test_tenant_id),
                        "project_id": str(pid),
                        "payload": {
                            "name": name,
                            "description": description,
                            "tags": list(tags),
                            "visibility": visibility,
                        },
                    },
                    s,
                    fake_provider,
                )
                await s.commit()
            return pid

    yield Seeder()
    async with TestingSessionLocal() as s:
        await s.execute(
            text("DELETE FROM embeddings WHERE tenant_id = :t"), {"t": test_tenant_id}
        )
        await s.commit()
