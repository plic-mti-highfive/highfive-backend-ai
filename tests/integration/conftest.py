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
