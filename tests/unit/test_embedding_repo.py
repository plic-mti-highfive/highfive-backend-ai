import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import set_tenant_context
from src.models.embedding import EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository


@pytest.mark.asyncio
async def test_create_and_get_embedding(db_session: AsyncSession, test_tenant_id):
    entity_id = uuid.uuid4()
    entity_type = EntityType.PROJECT

    # Set tenant context for RLS
    await set_tenant_context(db_session, test_tenant_id)

    repo = EmbeddingRepository(db_session, test_tenant_id)

    vector_data = [0.1] * 1536

    created_embedding = await repo.create(
        entity_type=entity_type,
        entity_id=entity_id,
        vector_data=vector_data,
        vector_purpose=VectorPurpose.IDENTITY,
        payload_metadata={},
    )

    assert created_embedding.id is not None
    assert created_embedding.tenant_id == test_tenant_id
    assert created_embedding.entity_type == entity_type
    assert created_embedding.entity_id == entity_id

    assert len(created_embedding.vector_data) == 1536

    fetched_embedding = await repo.get_by_entity(entity_id=entity_id)

    assert fetched_embedding is not None
    assert fetched_embedding.id == created_embedding.id
    assert fetched_embedding.entity_id == entity_id


@pytest.mark.asyncio
async def test_rls_isolation(db_session: AsyncSession):
    """Test that RLS isolates data by tenant_id using separate sessions"""
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    # Create embedding for tenant 1 with session
    await set_tenant_context(db_session, tenant1_id)
    repo1 = EmbeddingRepository(db_session, tenant1_id)
    vector_data = [0.1] * 1536

    created_embedding = await repo1.create(
        entity_type=EntityType.USER,
        entity_id=entity_id,
        vector_data=vector_data,
        vector_purpose=VectorPurpose.IDENTITY,
        payload_metadata={},
    )
    assert created_embedding.tenant_id == tenant1_id
    await db_session.flush()

    # Try to access with tenant 2 in same session
    await set_tenant_context(db_session, tenant2_id)
    await db_session.execute(text("SET ROLE api_tester"))

    repo2 = EmbeddingRepository(db_session, tenant2_id)
    fetched = await repo2.get_by_entity(entity_id=entity_id)

    assert fetched is None, "RLS failed: Tenant 2 should not be able to read Tenant 1's data!"


@pytest.mark.asyncio
async def test_update_replaces_vector_and_metadata(db_session: AsyncSession, test_tenant_id):
    entity_id = uuid.uuid4()
    await set_tenant_context(db_session, test_tenant_id)
    repo = EmbeddingRepository(db_session, test_tenant_id)
    await repo.create(EntityType.USER, entity_id, [0.1] * 1536, VectorPurpose.IDENTITY, {"a": 1})

    updated = await repo.update(entity_id, VectorPurpose.IDENTITY, [0.2] * 1536, {"b": 2})

    assert updated.payload_metadata == {"b": 2}
    assert updated.vector_data[0] == pytest.approx(0.2)
    fetched = await repo.get_by_entity_and_purpose(entity_id, VectorPurpose.IDENTITY)
    assert fetched.payload_metadata == {"b": 2}


@pytest.mark.asyncio
async def test_update_unknown_embedding_raises(db_session: AsyncSession, test_tenant_id):
    await set_tenant_context(db_session, test_tenant_id)
    repo = EmbeddingRepository(db_session, test_tenant_id)
    with pytest.raises(ValueError, match="not found"):
        await repo.update(uuid.uuid4(), VectorPurpose.IDENTITY, [0.2] * 1536, {})


@pytest.mark.asyncio
async def test_get_all_returns_only_current_tenant(db_session: AsyncSession, test_tenant_id):
    other_tenant = uuid.uuid4()
    await set_tenant_context(db_session, test_tenant_id)
    mine = EmbeddingRepository(db_session, test_tenant_id)
    theirs = EmbeddingRepository(db_session, other_tenant)
    ids = {uuid.uuid4(), uuid.uuid4()}
    for eid in ids:
        await mine.create(EntityType.USER, eid, [0.1] * 1536, VectorPurpose.IDENTITY, {})
    await theirs.create(EntityType.USER, uuid.uuid4(), [0.1] * 1536, VectorPurpose.IDENTITY, {})

    assert {e.entity_id for e in await mine.get_all()} == ids
    assert await EmbeddingRepository(db_session, uuid.uuid4()).get_all() == []


@pytest.mark.asyncio
async def test_get_by_entity_ignores_other_tenant(db_session: AsyncSession, test_tenant_id):
    entity_id = uuid.uuid4()
    await set_tenant_context(db_session, test_tenant_id)
    await EmbeddingRepository(db_session, test_tenant_id).create(
        EntityType.USER, entity_id, [0.1] * 1536, VectorPurpose.IDENTITY, {}
    )
    stranger = EmbeddingRepository(db_session, uuid.uuid4())
    assert await stranger.get_by_entity(entity_id) is None
    assert await stranger.get_by_entity_and_purpose(entity_id, VectorPurpose.IDENTITY) is None
    assert await stranger.find_nearest_neighbors(
        [0.1] * 1536, EntityType.USER, VectorPurpose.IDENTITY
    ) == []
