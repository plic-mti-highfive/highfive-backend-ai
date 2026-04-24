import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
