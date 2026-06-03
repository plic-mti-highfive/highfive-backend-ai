import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import set_tenant_context
from src.models.embedding import EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository
from src.services.matchmaking_service import MatchmakingService


@pytest.mark.asyncio
async def test_get_project_recommendations_integration(db_session: AsyncSession, test_tenant_id):
    user_id = uuid.uuid4()
    perfect_match_project_id = uuid.uuid4()
    bad_match_project_id = uuid.uuid4()

    await set_tenant_context(db_session, test_tenant_id)
    await db_session.execute(text("SET ROLE api_tester"))

    repo = EmbeddingRepository(db_session, test_tenant_id)
    service = MatchmakingService(repo)

    user_vector = [1.0] + [0.0] * 1535
    await repo.create(
        entity_type=EntityType.USER,
        entity_id=user_id,
        vector_data=user_vector,
        vector_purpose=VectorPurpose.IDENTITY,
        payload_metadata={},
    )

    # Project A : Same vector as user, should be top recommendation
    await repo.create(
        entity_type=EntityType.PROJECT,
        entity_id=perfect_match_project_id,
        vector_data=user_vector,
        vector_purpose=VectorPurpose.IDENTITY,
        payload_metadata={},
    )

    # Project B : Opposite vector, should not be recommended
    bad_vector = [0.0, 1.0] + [0.0] * 1534
    await repo.create(
        entity_type=EntityType.PROJECT,
        entity_id=bad_match_project_id,
        vector_data=bad_vector,
        vector_purpose=VectorPurpose.IDENTITY,
        payload_metadata={},
    )

    recommendations = await service.get_project_recommendations_for_user(user_id=user_id, limit=2)

    assert len(recommendations) == 2
    assert recommendations[0].id == perfect_match_project_id
    assert recommendations[0].position == 0
    assert recommendations[1].id == bad_match_project_id
    assert recommendations[1].position == 1
