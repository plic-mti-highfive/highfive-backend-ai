import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.interfaces.llm_provider import ILLMProvider
from src.repositories.embedding_repository import EmbeddingRepository
from src.services.embedding_service import EmbeddingService


async def handle_user_identity(
    data: dict, session: AsyncSession, llm_provider: ILLMProvider
) -> None:
    """Process user identity embedding generation."""
    tenant_id = uuid.UUID(data["tenant_id"])
    user_id = uuid.UUID(data["user_id"])

    repo = EmbeddingRepository(session, tenant_id)
    service = EmbeddingService(llm_provider, repo, tenant_id)

    await service.process_user_identity(user_id=user_id, payload=data.get("payload", {}))


async def handle_project_identity(
    data: dict, session: AsyncSession, llm_provider: ILLMProvider
) -> None:
    """Process project identity embedding generation."""
    tenant_id = uuid.UUID(data["tenant_id"])
    project_id = uuid.UUID(data["project_id"])

    repo = EmbeddingRepository(session, tenant_id)
    service = EmbeddingService(llm_provider, repo, tenant_id)

    await service.process_project_identity(project_id=project_id, payload=data.get("payload", {}))
