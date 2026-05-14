import math
import uuid

from src.core.logger import get_logger
from src.models.embedding import EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository
from src.schemas.embeddings import RecommendationResultItem

logger = get_logger(__name__)


class MatchmakingService:
    def __init__(self, embedding_repo: EmbeddingRepository):
        self.embedding_repo = embedding_repo

    def _combine_vectors(
        self, v1: list[float], v2: list[float], weight_v1: float = 0.8
    ) -> list[float]:
        weight_v2 = 1.0 - weight_v1
        combined = [(a * weight_v1) + (b * weight_v2) for a, b in zip(v1, v2)]

        magnitude = math.sqrt(sum(v**2 for v in combined))
        return [v / magnitude for v in combined] if magnitude > 0 else combined

    async def get_user_recommendations_for_project(
        self, project_id: uuid.UUID, limit: int = 10
    ) -> list[RecommendationResultItem]:
        """
        Get user recommendations for a project based on vector similarity between the project's
        CONTENT vector and users' IDENTITY vectors.
        """
        logger.info(f"Fetching user recommendations for project {project_id} (limit: {limit})")
        project_vector_obj = await self.embedding_repo.get_by_entity_and_purpose(
            entity_id=project_id, purpose=VectorPurpose.IDENTITY
        )

        if not project_vector_obj:
            logger.warning(
                "No identity vector found for project "
                f"{project_id}, returning empty recommendations"
            )
            return []

        logger.debug("Project identity vector retrieved, searching for similar users")
        closest_users = await self.embedding_repo.find_nearest_neighbors(
            target_vector=project_vector_obj.vector_data,
            target_entity_type=EntityType.USER,
            target_purpose=VectorPurpose.IDENTITY,
            limit=limit,
        )
        logger.info(f"Found {len(closest_users)} user recommendations for project {project_id}")
        return [
            RecommendationResultItem(id=user.entity_id, position=i, metadata=user.payload_metadata)
            for i, user in enumerate(closest_users)
        ]

    async def get_project_recommendations_for_user(
        self, user_id: uuid.UUID, tags: list[str] | None = None, limit: int = 10
    ) -> list[RecommendationResultItem]:
        """
        Get project recommendations for a user based on vector similarity between the user's
        combined INTEREST/IDENTITY vector and projects' IDENTITY vectors. Optionally filter by tags.
        """

        target_vector = None
        interest_emb = await self.embedding_repo.get_by_entity_and_purpose(
            user_id, VectorPurpose.INTEREST
        )
        identity_emb = await self.embedding_repo.get_by_entity_and_purpose(
            user_id, VectorPurpose.IDENTITY
        )

        # Dual Vector
        if interest_emb and identity_emb:
            target_vector = self._combine_vectors(
                interest_emb.vector_data, identity_emb.vector_data, weight_v1=0.8
            )
        elif interest_emb:
            target_vector = interest_emb.vector_data
        elif identity_emb:
            target_vector = identity_emb.vector_data

        recommended_projects = await self.embedding_repo.search_projects(
            target_vector=target_vector, tags_filter=tags, limit=limit
        )

        return [
            RecommendationResultItem(id=proj.entity_id, position=i, metadata=proj.payload_metadata)
            for i, proj in enumerate(recommended_projects)
        ]

    async def get_trending_projects(self, limit: int = 10) -> list[RecommendationResultItem]:
        """
        Get trending projects based on recent interactions and time-decay.
        This will return projects that are currently popular, giving more weight to recent interactions.
        """
        trending_projects = await self.embedding_repo.get_trending_projects(limit=limit)

        return [
            RecommendationResultItem(
                id=proj.entity_id, position=idx, metadata=proj.payload_metadata
            )
            for idx, proj in enumerate(trending_projects)
        ]
