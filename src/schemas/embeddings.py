import uuid

from pydantic import BaseModel, Field


class UserEmbeddingPayload(BaseModel):
    entity_id: uuid.UUID
    bio: str | None = None
    skills: list[str] = Field(default_factory=list)


class ProjectEmbeddingPayload(BaseModel):
    entity_id: uuid.UUID
    name: str
    description: str | None = None


class EmbeddingResponse(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    entity_type: str
    message: str
