import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.embedding import Embedding, EntityType


class EmbeddingRepository:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def create(
        self,
        entity_type: EntityType,
        entity_id: uuid.UUID,
        vector_data: list[float],
    ) -> Embedding:
        """Create an embedding for the current tenant."""
        db_obj = Embedding(
            tenant_id=self.tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            vector_data=vector_data,
        )
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def get_by_entity(self, entity_id: uuid.UUID) -> Embedding | None:
        """Get an embedding by entity_id for the current tenant. RLS will enforce tenant_id isolation."""
        stmt = select(Embedding).where(Embedding.entity_id == entity_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Embedding]:
        """Get all embeddings for the current tenant. RLS will enforce tenant_id isolation."""
        stmt = select(Embedding)
        result = await self.db.execute(stmt)
        return result.scalars().all()
