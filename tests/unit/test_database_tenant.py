"""get_db_with_tenant : le contexte tenant (RLS) est posé puis nettoyé."""

import uuid

import pytest
from sqlalchemy import text

from src.infrastructure.database import AsyncSessionLocal, get_db_with_tenant


async def _current_tenant(session) -> str:
    row = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
    return row.scalar_one()


@pytest.mark.asyncio
async def test_get_db_with_tenant_sets_tenant_context():
    tenant_id = uuid.uuid4()
    async with get_db_with_tenant(tenant_id) as session:
        assert await _current_tenant(session) == str(tenant_id)


@pytest.mark.asyncio
async def test_get_db_with_tenant_clears_context_on_exit_even_on_error():
    tenant_id = uuid.uuid4()
    captured = {}
    with pytest.raises(RuntimeError):
        async with get_db_with_tenant(tenant_id) as session:
            captured["session"] = session
            raise RuntimeError("boom")
    # Session fermée : une nouvelle session du pool ne doit pas hériter du tenant précédent.
    async with get_db_with_tenant(uuid.uuid4()) as other:
        assert await _current_tenant(other) != str(tenant_id)
    async with AsyncSessionLocal() as fresh:
        assert await _current_tenant(fresh) in (None, "")
