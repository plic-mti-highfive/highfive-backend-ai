import uuid

from src.models.embedding import EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository


class MatchmakingService:
    def __init__(self, embedding_repo: EmbeddingRepository):
        self.embedding_repo = embedding_repo

    async def get_project_recommendations_for_user(
        self, user_id: uuid.UUID, limit: int = 10
    ) -> list[uuid.UUID]:
        """
        Get project recommendations for a user based on vector similarity between the user's
        IDENTITY vector and projects' CONTENT vectors.
        """
        user_vector_obj = await self.embedding_repo.get_by_entity_and_purpose(
            entity_id=user_id, purpose=VectorPurpose.IDENTITY
        )

        if not user_vector_obj:
            return []

        closest_projects = await self.embedding_repo.find_nearest_neighbors(
            target_vector=user_vector_obj.vector_data,
            target_entity_type=EntityType.PROJECT,
            target_purpose=VectorPurpose.CONTENT,
            limit=limit,
        )

        return [project.entity_id for project in closest_projects]

    async def get_user_recommendations_for_project(
        self, project_id: uuid.UUID, limit: int = 10
    ) -> list[uuid.UUID]:
        """
        Get user recommendations for a project based on vector similarity between the project's
        CONTENT vector and users' IDENTITY vectors.
        """
        project_vector_obj = await self.embedding_repo.get_by_entity_and_purpose(
            entity_id=project_id, purpose=VectorPurpose.CONTENT
        )

        if not project_vector_obj:
            return []

        closest_users = await self.embedding_repo.find_nearest_neighbors(
            target_vector=project_vector_obj.vector_data,
            target_entity_type=EntityType.USER,
            target_purpose=VectorPurpose.IDENTITY,
            limit=limit,
        )

        return [user.entity_id for user in closest_users]
