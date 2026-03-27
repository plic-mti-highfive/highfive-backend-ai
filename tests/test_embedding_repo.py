import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.embedding import EntityType
from src.repositories.embedding_repository import EmbeddingRepository


@pytest.mark.asyncio
async def test_create_and_get_embedding(db_session: AsyncSession):
    repo = EmbeddingRepository(db_session)

    tenant_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    entity_type = EntityType.PROJECT

    vector_data = [0.1] * 1536

    created_embedding = await repo.create(
        tenant_id=tenant_id, entity_type=entity_type, entity_id=entity_id, vector_data=vector_data
    )

    assert created_embedding.id is not None
    assert created_embedding.tenant_id == tenant_id
    assert created_embedding.entity_type == entity_type
    assert created_embedding.entity_id == entity_id

    assert len(created_embedding.vector_data) == 1536

    fetched_embedding = await repo.get_by_entity(entity_id=entity_id)

    assert fetched_embedding is not None
    assert fetched_embedding.id == created_embedding.id
    assert fetched_embedding.entity_id == entity_id
