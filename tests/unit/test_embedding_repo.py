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
