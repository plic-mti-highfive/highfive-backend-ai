import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from src.api.dependencies import get_current_user
from src.infrastructure.database import set_tenant_context
from src.models.embedding import EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository
from src.server import create_app

app = create_app()


@pytest.fixture(autouse=True)
def setup_test_auth(test_tenant_id):
    """
    Set up auth for each test with unique tenant_id.
    This ensures test isolation even if data persists in DB.
    """

    def override_get_current_user():
        return {"sub": str(uuid.uuid4()), "tenantId": str(test_tenant_id)}

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_projects_for_user_api(db_session, test_tenant_id):
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    await set_tenant_context(db_session, test_tenant_id)
    await db_session.execute(text("SET ROLE api_tester"))
    repo = EmbeddingRepository(db_session, test_tenant_id)

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
        vector_purpose=VectorPurpose.IDENTITY,
        payload_metadata={
            "theme": "Informatique",
            "sub_themes": ["Backend", "APIs"],
        },
    )
    await db_session.commit()  # Necessary for AsyncClient to see data

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
    assert data[0]["id"] == str(project_id)
    assert data[0]["position"] == 0
    assert data[0]["metadata"]["theme"] == "Informatique"
    assert "Backend" in data[0]["metadata"]["sub_themes"]
    assert "APIs" in data[0]["metadata"]["sub_themes"]
