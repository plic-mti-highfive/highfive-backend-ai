import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.embedding import Embedding, EntityType


class EmbeddingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        tenant_id: uuid.UUID,
        entity_type: EntityType,
        entity_id: uuid.UUID,
        vector_data: list[float],
    ) -> Embedding:
        db_obj = Embedding(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            vector_data=vector_data,
        )
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def get_by_entity(self, entity_id: uuid.UUID) -> Embedding | None:
        stmt = select(Embedding).where(Embedding.entity_id == entity_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
