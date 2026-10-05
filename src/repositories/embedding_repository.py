import uuid

from sqlalchemy import Float, Row, cast, func, literal, nulls_last, select, update
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TRENDING_GRAVITY
from src.models.embedding import Embedding, EntityType, VectorPurpose


def _merge_jsonb(column, other):
    """Expression SQL `coalesce(column, '{}') || other` (fusion JSONB, `other` prioritaire)."""
    return func.coalesce(column, literal({}, JSONB)).op("||")(other)


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

    async def update(
        self,
        entity_id: uuid.UUID,
        vector_purpose: VectorPurpose,
        vector_data: list[float],
        payload_metadata: dict,
    ) -> Embedding:
        """Update an existing embedding for the current tenant."""
        embedding = await self.get_by_entity_and_purpose(entity_id, vector_purpose)
        if not embedding:
            raise ValueError(
                f"Embedding not found for entity {entity_id} with purpose {vector_purpose}"
            )

        embedding.vector_data = vector_data
        embedding.payload_metadata = payload_metadata
        await self.db.flush()
        return embedding

    async def get_by_entity(self, entity_id: uuid.UUID) -> Embedding | None:
        """
        Get an embedding by entity_id for the current tenant.

        RLS will enforce tenant_id isolation.
        """
        stmt = (
            select(Embedding)
            .where(Embedding.entity_id == entity_id, Embedding.tenant_id == self.tenant_id)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_all(self) -> list[Embedding]:
        """
        Get all embeddings for the current tenant.

        RLS will enforce tenant_id isolation.
        """
        stmt = select(Embedding).where(Embedding.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_entity_and_purpose(
        self, entity_id: uuid.UUID, purpose: VectorPurpose
    ) -> Embedding | None:
        """
        Get an embedding by entity_id and vector_purpose for the current tenant.

        RLS will enforce tenant_id isolation.
        """
        stmt = select(Embedding).where(
            Embedding.entity_id == entity_id,
            Embedding.vector_purpose == purpose,
            Embedding.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many(
        self, entity_ids: list[uuid.UUID], purposes: list[VectorPurpose]
    ) -> dict[tuple[uuid.UUID, VectorPurpose], Embedding]:
        """Récupère plusieurs embeddings en une seule requête, indexés par (entité, usage)."""
        stmt = select(Embedding).where(
            Embedding.entity_id.in_(entity_ids),
            Embedding.vector_purpose.in_(purposes),
            Embedding.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(stmt)
        return {(e.entity_id, e.vector_purpose): e for e in result.scalars().all()}

    async def get_for_update(
        self, entity_id: uuid.UUID, purpose: VectorPurpose
    ) -> Embedding | None:
        """Comme get_by_entity_and_purpose, mais verrouille la ligne (FOR UPDATE)."""
        stmt = (
            select(Embedding)
            .where(
                Embedding.entity_id == entity_id,
                Embedding.vector_purpose == purpose,
                Embedding.tenant_id == self.tenant_id,
            )
            .with_for_update()
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_content_hash(self, entity_id: uuid.UUID, purpose: VectorPurpose) -> str | None:
        """Hash du contenu source déjà vectorisé (sans charger le vecteur de 1536 floats)."""
        stmt = select(Embedding.content_hash).where(
            Embedding.entity_id == entity_id,
            Embedding.vector_purpose == purpose,
            Embedding.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        entity_type: EntityType,
        entity_id: uuid.UUID,
        vector_data: list[float],
        vector_purpose: VectorPurpose,
        payload_metadata: dict,
        content_hash: str | None = None,
    ) -> None:
        """
        Insère ou met à jour atomiquement (INSERT ... ON CONFLICT) l'embedding d'une entité.

        Les métadonnées sont fusionnées (`||`) avec l'existant : les compteurs écrits par d'autres
        jobs (ex: `likes`) ne sont pas écrasés par une mise à jour d'identité.
        """
        stmt = pg_insert(Embedding).values(
            tenant_id=self.tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            vector_data=vector_data,
            vector_purpose=vector_purpose,
            payload_metadata=payload_metadata,
            content_hash=content_hash,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "entity_id", "vector_purpose"],
            set_={
                "vector_data": stmt.excluded.vector_data,
                "payload_metadata": func.coalesce(
                    Embedding.payload_metadata, literal({}, JSONB)
                ).op("||")(stmt.excluded.payload_metadata),
                "content_hash": stmt.excluded.content_hash,
                "updated_at": func.now(),
            },
        )
        await self.db.execute(stmt)

    async def insert_if_absent(
        self,
        entity_type: EntityType,
        entity_id: uuid.UUID,
        vector_data: list[float],
        vector_purpose: VectorPurpose,
        payload_metadata: dict,
    ) -> None:
        """INSERT ... ON CONFLICT DO NOTHING : sûr si deux jobs initialisent la même ligne."""
        stmt = (
            pg_insert(Embedding)
            .values(
                tenant_id=self.tenant_id,
                entity_type=entity_type,
                entity_id=entity_id,
                vector_data=vector_data,
                vector_purpose=vector_purpose,
                payload_metadata=payload_metadata,
            )
            .on_conflict_do_nothing(index_elements=["tenant_id", "entity_id", "vector_purpose"])
        )
        await self.db.execute(stmt)

    async def patch_metadata(
        self, entity_id: uuid.UUID, purpose: VectorPurpose, patch: dict
    ) -> int:
        """Fusionne `patch` dans payload_metadata (atomique). Retourne le nombre de lignes."""
        stmt = (
            update(Embedding)
            .where(
                Embedding.entity_id == entity_id,
                Embedding.vector_purpose == purpose,
                Embedding.tenant_id == self.tenant_id,
            )
            .values(
                payload_metadata=_merge_jsonb(Embedding.payload_metadata, literal(patch, JSONB))
            )
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def find_nearest_neighbors(
        self,
        target_vector: list[float],
        target_entity_type: EntityType,
        target_purpose: VectorPurpose,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> list[Row]:
        """
        Find nearest neighbors to a target vector for a given entity type and purpose.

        min_similarity: Cosine distance threshold (0-2). Lower = more similar.
        Default 0.5 filters weak matches.
        RLS will enforce tenant_id isolation.
        """
        distance = Embedding.vector_data.cosine_distance(target_vector).label("distance")
        stmt = (
            select(Embedding.entity_id, Embedding.payload_metadata)
            .where(
                Embedding.tenant_id == self.tenant_id,
                Embedding.entity_type == target_entity_type,
                Embedding.vector_purpose == target_purpose,
                distance < min_similarity,
            )
            .order_by(distance)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    def _get_trending_score_expr(self):
        """
        Get a SQL expression to calculate a trending score based on likes and recency for projects.
        Formule: trending_score = (likes + 1) / ((age_in_hours + 2) ^ gravity)
        """
        likes = func.coalesce(cast(Embedding.payload_metadata["likes"].astext, Float), 0.0)

        age_in_hours = func.extract("epoch", func.now() - Embedding.updated_at) / 3600.0

        trending_score = (likes + 1.0) / func.power((age_in_hours + 2.0), TRENDING_GRAVITY)

        return trending_score

    async def get_trending_projects(self, limit: int = 10) -> list[Row]:
        """
        Get trending projects for the current tenant.
        """
        trending_expr = self._get_trending_score_expr()

        stmt = (
            select(Embedding.entity_id, Embedding.payload_metadata)
            .where(
                Embedding.entity_type == EntityType.PROJECT, Embedding.tenant_id == self.tenant_id
            )
            .order_by(nulls_last(trending_expr.desc()))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.all())

    async def search_projects(
        self,
        target_vector: list[float] | None = None,
        tags_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[Row]:
        """
        Search for projects using a hybrid approach:
        - If a target_vector is provided, perform AI matchmaking.
        - If no target_vector is provided (e.g. cold start), fall back to trending.
        - If tags are provided, filter projects that have matching tags in their payload_metadata.
        """
        stmt = select(Embedding.entity_id, Embedding.payload_metadata).where(
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

        return list(result.all())
