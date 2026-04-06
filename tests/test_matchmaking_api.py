import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_current_user
from src.infrastructure.database import set_tenant_context
from src.models.embedding import EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository
from src.server import create_app

app = create_app()

TEST_TENANT_ID = uuid.uuid4()
TEST_USER_PAYLOAD = {"sub": str(uuid.uuid4()), "tenant_id": str(TEST_TENANT_ID)}


def override_get_current_user():
    return TEST_USER_PAYLOAD


app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.mark.asyncio
async def test_get_projects_for_user_api(db_session):
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    await set_tenant_context(db_session, TEST_TENANT_ID)
    repo = EmbeddingRepository(db_session, TEST_TENANT_ID)

    vector = [0.5] * 1536
    await repo.create(
        entity_type=EntityType.USER,
        entity_id=user_id,
        vector_data=vector,
        vector_purpose=VectorPurpose.IDENTITY,
        payload_metadata={},
    )
    await repo.create(
        entity_type=EntityType.PROJECT,
        entity_id=project_id,
        vector_data=vector,
        vector_purpose=VectorPurpose.CONTENT,
        payload_metadata={},
    )
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            f"/api/v1/matchmaking/users/{user_id}/projects?limit=5",
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0] == str(project_id)
