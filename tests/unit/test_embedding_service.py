import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import set_tenant_context
from src.models.embedding import Embedding, EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository
from src.services.embedding_service import EmbeddingService


@pytest.fixture
def mock_llm_provider():
    mock = AsyncMock()
    mock.generate_embedding.return_value = [0.5] * 1536
    mock.extract_metadata.return_value = {
        "theme": "Informatique",
        "sub_themes": ["Backend", "APIs"],
    }
    return mock


@pytest.mark.asyncio
async def test_process_user_identity_integration(
    db_session: AsyncSession, test_tenant_id, mock_llm_provider
):
    user_id = uuid.uuid4()

    await set_tenant_context(db_session, test_tenant_id)
    await db_session.execute(text("SET ROLE api_tester"))

    repo = EmbeddingRepository(db_session, test_tenant_id)
    service = EmbeddingService(mock_llm_provider, repo, test_tenant_id)

    payload = {"bio": "Développeur passionné de <p>Python</p>", "skills": ["FastAPI", "Docker"]}
    await service.process_user_identity(user_id=user_id, payload=payload)

    stmt = select(Embedding).where(
        Embedding.entity_id == user_id, Embedding.vector_purpose == VectorPurpose.IDENTITY
    )
    result = await db_session.execute(stmt)
    saved_embedding = result.scalar_one_or_none()

    assert saved_embedding is not None
    assert saved_embedding.entity_type == EntityType.USER
    assert saved_embedding.tenant_id == test_tenant_id
    assert saved_embedding.payload_metadata == {"skills_count": 2}
    assert (saved_embedding.vector_data == 0.5).all()

    mock_llm_provider.generate_embedding.assert_called_once_with(
        "Biographie : développeur passionner python. Compétences : fastapi docker."
    )


@pytest.mark.asyncio
async def test_process_project_identity_integration(
    db_session: AsyncSession, test_tenant_id, mock_llm_provider
):
    project_id = uuid.uuid4()

    await set_tenant_context(db_session, test_tenant_id)
    await db_session.execute(text("SET ROLE api_tester"))

    repo = EmbeddingRepository(db_session, test_tenant_id)
    service = EmbeddingService(mock_llm_provider, repo, test_tenant_id)

    payload = {
        "name": "Mon projet <b>awesome</b>",
        "description": "Une description super cool",
        "tags": ["Python", "FastAPI", "Docker"],
        "visibility": "PRIVATE",
    }
    await service.process_project_identity(project_id=project_id, payload=payload)

    stmt = select(Embedding).where(
        Embedding.entity_id == project_id, Embedding.vector_purpose == VectorPurpose.IDENTITY
    )
    result = await db_session.execute(stmt)
    saved_embedding = result.scalar_one_or_none()

    assert saved_embedding is not None
    assert saved_embedding.entity_type == EntityType.PROJECT
    assert saved_embedding.tenant_id == test_tenant_id
    assert saved_embedding.payload_metadata == {
        "visibility": "PRIVATE",
        "theme": "Informatique",
        "sub_themes": ["Backend", "APIs"],
    }
    assert (saved_embedding.vector_data == 0.5).all()

    mock_llm_provider.generate_embedding.assert_called_once_with(
        "Nom du projet : projet awesom. Description : description super cool. Technologies et mots-clés : python fastapi docker."
    )
    mock_llm_provider.extract_metadata.assert_called_once_with(
        "Nom du projet : projet awesom. Description : description super cool. Technologies et mots-clés : python fastapi docker."
    )
