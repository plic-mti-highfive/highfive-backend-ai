import asyncio
import uuid

from src.core.text_processor import TextProcessor
from src.infrastructure.llm_provider import ILLMProvider
from src.models.embedding import EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository

# USER
USER_IDENTITY_SCHEMA = {
    "bio": "Biographie : {}.",
    "skills": "Compétences : {}.",
}
USER_INTEREST_SCHEMA = {}

# PROJECT
PROJECT_IDENTITY_SCHEMA = {
    "name": "Nom du projet : {}.",
    "description": "Description : {}.",
    "tags": "Technologies et mots-clés : {}.",
}
PROJECT_CONTENT_SCHEMA = {}

# TICKET
TICKET_CONTENT_SCHEMA = {
    "name": "Nom du projet : {}.",
    "description": "Description : {}.",
    "tags": "Technologies et mots-clés : {}.",
}


class EmbeddingService:
    def __init__(
        self, llm_provider: ILLMProvider, embedding_repo: EmbeddingRepository, tenant_id: uuid.UUID
    ):
        self.llm_provider = llm_provider
        self.embedding_repo = embedding_repo
        self.tenant_id = tenant_id

    async def process_user_identity(
        self,
        user_id: uuid.UUID,
        payload: dict,
    ) -> None:
        """
        Génère et sauvegarde le vecteur d'IDENTITÉ d'un utilisateur.
        À appeler quand l'utilisateur met à jour son profil NestJS.
        """
        text_to_vectorize = TextProcessor.build_text_from_schema(payload, USER_IDENTITY_SCHEMA)

        vector_data = await self.llm_provider.generate_embedding(text_to_vectorize)

        await self.embedding_repo.create(
            entity_type=EntityType.USER,
            entity_id=user_id,
            vector_data=vector_data,
            vector_purpose=VectorPurpose.IDENTITY,
            payload_metadata={"skills_count": len(payload.get("skills", []))},
        )

    async def process_project_identity(
        self,
        project_id: uuid.UUID,
        payload: dict,
    ) -> None:

        text_to_vectorize = TextProcessor.build_text_from_schema(payload, PROJECT_IDENTITY_SCHEMA)

        vector_task = self.llm_provider.generate_embedding(text_to_vectorize)
        metadata_task = self.llm_provider.extract_metadata(text_to_vectorize)

        vector_data, extracted_meta = await asyncio.gather(vector_task, metadata_task)

        final_metadata = {
            "visibility": payload.get("visibility", "PUBLIC"),
            "theme": extracted_meta.get("theme"),
            "sub_themes": extracted_meta.get("sub_themes", []),
        }

        await self.embedding_repo.create(
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            vector_data=vector_data,
            vector_purpose=VectorPurpose.IDENTITY,
            payload_metadata=final_metadata,
        )
