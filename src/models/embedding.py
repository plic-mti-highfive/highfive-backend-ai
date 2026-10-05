import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Enum, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, mapped_column

Base = declarative_base()


class EntityType(str, enum.Enum):
    USER = "USER"
    PROJECT = "PROJECT"
    TICKET = "TICKET"


class VectorPurpose(str, enum.Enum):
    IDENTITY = "IDENTITY"  # Who I am
    INTEREST = "INTEREST"  # What I like
    CONTENT = "CONTENT"  # Static content


class Embedding(Base):
    __tablename__ = "embeddings"

    # id UUID PK
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # tenant_id UUID NOT NULL
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # entity_type ENUM
    entity_type = Column(Enum(EntityType, name="entity_type_enum"), nullable=False, index=True)

    # entity_id UUID Polymorphique
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # vector_purpose ENUM
    vector_purpose = Column(
        Enum(VectorPurpose, name="vector_purpose_enum"),
        nullable=False,
        default=VectorPurpose.CONTENT,
    )

    # vector_data VECTOR(1536) pgvector
    vector_data = mapped_column(Vector(1536), nullable=False)  # OPENAI text-embedding-3-small

    # payload_metadata JSONB
    payload_metadata = Column(JSONB, nullable=True)

    # content_hash : SHA-256 du contenu source (+ modèle), pour ignorer les recalculs inutiles
    content_hash = Column(String(64), nullable=True)

    # updated_at TIMESTAMP DEFAULT NOW()
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Une seule ligne par (tenant, entité, usage) : permet l'upsert atomique
        Index(
            "uq_embeddings_tenant_entity_purpose",
            "tenant_id",
            "entity_id",
            "vector_purpose",
            unique=True,
        ),
        # GIN index for payload_metadata to speed up JSONB queries
        Index(
            "ix_embeddings_payload_metadata_gin",
            "payload_metadata",
            postgresql_using="gin",
        ),
        # HNSW index for vector_data to speed up vector queries
        Index(
            "ix_embeddings_vector_data_hnsw",
            "vector_data",
            postgresql_using="hnsw",
            postgresql_ops={"vector_data": "vector_cosine_ops"},
        ),
    )
