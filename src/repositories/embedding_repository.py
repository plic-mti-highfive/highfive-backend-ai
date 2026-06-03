import uuid

from sqlalchemy import Float, cast, func, nulls_last, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TRENDING_GRAVITY
from src.models.embedding import Embedding, EntityType, VectorPurpose


class EmbeddingRepository:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def create(
        self,
        entity_type: EntityType,
        entity_id: uuid.UUID,
        vector_data: list[float],
        vector_purpose: VectorPurpose,
        payload_metadata: dict,
    ) -> Embedding:
        """Create an embedding for the current tenant."""
        db_obj = Embedding(
            tenant_id=self.tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            vector_data=vector_data,
            vector_purpose=vector_purpose,
            payload_metadata=payload_metadata,
        )
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def get_by_entity(self, entity_id: uuid.UUID) -> Embedding | None:
        """
        Get an embedding by entity_id for the current tenant.

        RLS will enforce tenant_id isolation.
        """
        stmt = select(Embedding).where(Embedding.entity_id == entity_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Embedding]:
        """
        Get all embeddings for the current tenant.

        RLS will enforce tenant_id isolation.
        """
        stmt = select(Embedding)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_entity_and_purpose(
        self, entity_id: uuid.UUID, purpose: VectorPurpose
    ) -> Embedding | None:
        """
        Get an embedding by entity_id and vector_purpose for the current tenant.

        RLS will enforce tenant_id isolation.
        """
        stmt = select(Embedding).where(
            Embedding.entity_id == entity_id, Embedding.vector_purpose == purpose
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_nearest_neighbors(
        self,
        target_vector: list[float],
        target_entity_type: EntityType,
        target_purpose: VectorPurpose,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> list[Embedding]:
        """
        Find nearest neighbors to a target vector for a given entity type and purpose.

        min_similarity: Cosine distance threshold (0-2). Lower = more similar.
        Default 0.5 filters weak matches.
        RLS will enforce tenant_id isolation.
        """
        stmt = (
            select(Embedding)
            .where(
                Embedding.entity_type == target_entity_type,
                Embedding.vector_purpose == target_purpose,
                Embedding.vector_data.cosine_distance(target_vector) < min_similarity,
            )
            .order_by(Embedding.vector_data.cosine_distance(target_vector))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _get_trending_score_expr(self):
        """
        Get a SQL expression to calculate a trending score based on likes and recency for projects.
        Formule: trending_score = (likes + 1) / ((age_in_hours + 2) ^ gravity)
        """
        likes = func.coalesce(cast(Embedding.payload_metadata["likes"].astext, Float), 0.0)

        age_in_hours = func.extract("epoch", func.now() - Embedding.updated_at) / 3600.0

        trending_score = (likes + 1.0) / func.power((age_in_hours + 2.0), TRENDING_GRAVITY)

        return trending_score

    async def get_trending_projects(self, limit: int = 10) -> list[Embedding]:
        """
        Get trending projects for the current tenant.
        """
        trending_expr = self._get_trending_score_expr()

        stmt = (
            select(Embedding)
            .where(
                Embedding.entity_type == EntityType.PROJECT, Embedding.tenant_id == self.tenant_id
            )
            .order_by(nulls_last(trending_expr.desc()))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_projects(
        self,
        target_vector: list[float] | None = None,
        tags_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[Embedding]:
        """
        Search for projects using a hybrid approach:
        - If a target_vector is provided, perform AI matchmaking.
        - If no target_vector is provided (e.g. cold start), fall back to trending.
        - If tags are provided, filter projects that have matching tags in their payload_metadata.
        """
        stmt = select(Embedding).where(
            Embedding.entity_type == EntityType.PROJECT, Embedding.tenant_id == self.tenant_id
        )

        # Filter on tags if provided
        if tags_filter:
            stmt = stmt.where(Embedding.payload_metadata["theme"].has_any(array(tags_filter)))

        # 2. MATCHMAKING AI vs TRENDING
        if target_vector is not None:
            # If user has a interest vector, we use it for matchmaking
            stmt = stmt.order_by(Embedding.vector_data.cosine_distance(target_vector))
        else:
            # If no vector provided (ex: cold start), we fallback to trending algorithm
            trending_expr = self._get_trending_score_expr()
            stmt = stmt.order_by(nulls_last(trending_expr.desc()))

        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)

        return list(result.scalars().all())
