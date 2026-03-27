import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, mapped_column

Base = declarative_base()


class EntityType(str, enum.Enum):
    USER = "USER"
    PROJECT = "PROJECT"
    TICKET = "TICKET"


class ProjectEmbedding(Base):
    __tablename__ = "embeddings"

    # id UUID PK
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # tenant_id UUID NOT NULL
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # entity_type ENUM
    entity_type = Column(
        Enum(EntityType, name="entity_type_enum", create_type=False), nullable=False, index=True
    )

    # entity_id UUID Polymorphique
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # vector_data VECTOR(1536) pgvector
    vector_data = mapped_column(Vector(1536), nullable=False)  # OPENAI text-embedding-3-small

    # updated_at TIMESTAMP DEFAULT NOW()
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
