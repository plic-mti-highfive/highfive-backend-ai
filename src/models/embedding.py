import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Enum, func
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

    # paylod_metadata JSONB
    payload_metadata = Column(JSONB, nullable=True)

    # updated_at TIMESTAMP DEFAULT NOW()
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
