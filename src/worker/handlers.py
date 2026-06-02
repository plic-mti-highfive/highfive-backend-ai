import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.core.constants import InteractionType
from src.core.logger import get_logger
from src.infrastructure.llm_provider import ILLMProvider
from src.models.embedding import Embedding, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository
from src.services.embedding_service import EmbeddingService

logger = get_logger(__name__)


async def handle_user_identity(
    data: dict, session: AsyncSession, llm_provider: ILLMProvider
) -> None:
    """Process user identity embedding generation."""
    tenant_id = uuid.UUID(data["tenant_id"])
    user_id = uuid.UUID(data["user_id"])
    logger.info(f"Processing user identity for user {user_id} (tenant: {tenant_id})")

    repo = EmbeddingRepository(session, tenant_id)
    service = EmbeddingService(llm_provider, repo, tenant_id)

    await service.process_user_identity(user_id=user_id, payload=data.get("payload", {}))
    logger.info(f"User identity processing completed for user {user_id}")


async def handle_project_identity(
    data: dict, session: AsyncSession, llm_provider: ILLMProvider
) -> None:
    """Process project identity embedding generation."""
    tenant_id = uuid.UUID(data["tenant_id"])
    project_id = uuid.UUID(data["project_id"])
    logger.info(f"Processing project identity for project {project_id} (tenant: {tenant_id})")

    repo = EmbeddingRepository(session, tenant_id)
    service = EmbeddingService(llm_provider, repo, tenant_id)

    await service.process_project_identity(project_id=project_id, payload=data.get("payload", {}))
    logger.info(f"Project identity processing completed for project {project_id}")


async def handle_user_interaction(
    data: dict, session: AsyncSession, llm_provider: ILLMProvider
) -> None:
    """
    Process a user interaction to update their INTEREST vector.
    Expected data payload: { "tenant_id": "...", "user_id": "...", "project_id": "...", "interaction_type": "LIKE" }
    """
    tenant_id = uuid.UUID(data["tenant_id"])
    user_id = uuid.UUID(data["user_id"])
    project_id = uuid.UUID(data["project_id"])

    interaction_type = InteractionType(data["interaction_type"])

    logger.info(f"Processing {interaction_type} for user {user_id} on project {project_id}")

    repo = EmbeddingRepository(session, tenant_id)
    service = EmbeddingService(llm_provider, repo, tenant_id)

    await service.process_user_interaction(
        user_id=user_id, project_id=project_id, interaction_type=interaction_type
    )
    logger.info(f"Interaction processing completed for user {user_id}")


async def handle_project_stats_updated(
    data: dict, session: AsyncSession, llm_provider: ILLMProvider
) -> None:
    """
    Process a fast DB update when project stats (like 'likes' or 'views') change.
    Expected data: { "tenant_id": "...", "project_id": "...", "likes": 42 }
    """
    tenant_id = uuid.UUID(data["tenant_id"])
    project_id = uuid.UUID(data["project_id"])
    new_likes_count = data.get("likes", 0)

    logger.info(f"Updating stats for project {project_id} (likes: {new_likes_count})")

    stmt = select(Embedding).where(
        Embedding.entity_id == project_id,
        Embedding.vector_purpose == VectorPurpose.IDENTITY,
        Embedding.tenant_id == tenant_id,
    )
    result = await session.execute(stmt)
    embedding = result.scalar_one_or_none()

    if not embedding:
        raise ValueError(f"Project {project_id} not found. Retrying later...")

    if not embedding.payload_metadata:
        embedding.payload_metadata = {}

    embedding.payload_metadata["likes"] = new_likes_count

    flag_modified(embedding, "payload_metadata")

    logger.info(f"Stats successfully updated for project {project_id}")
