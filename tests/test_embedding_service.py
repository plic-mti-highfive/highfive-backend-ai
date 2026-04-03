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
    return mock


@pytest.mark.asyncio
async def test_process_user_identity_integration(db_session: AsyncSession, mock_llm_provider):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    await set_tenant_context(db_session, tenant_id)
    await db_session.execute(text("SET ROLE api_tester"))

    repo = EmbeddingRepository(db_session, tenant_id)
    service = EmbeddingService(mock_llm_provider, repo, tenant_id)

    await service.process_user_identity(
        user_id=user_id, bio="Développeur passionné de <p>Python</p>", skills=["FastAPI", "Docker"]
    )

    stmt = select(Embedding).where(
        Embedding.entity_id == user_id, Embedding.vector_purpose == VectorPurpose.IDENTITY
    )
    result = await db_session.execute(stmt)
    saved_embedding = result.scalar_one_or_none()

    assert saved_embedding is not None
    assert saved_embedding.entity_type == EntityType.USER
    assert saved_embedding.tenant_id == tenant_id
    assert saved_embedding.payload_metadata == {"skills_count": 2}
    assert (saved_embedding.vector_data == 0.5).all()

    mock_llm_provider.generate_embedding.assert_called_once_with(
        "Profil étudiant. Biographie : Développeur passionné de Python Compétences maîtrisées : FastAPI, Docker."
    )
