import uuid

from src.core.text_processor import TextProcessor
from src.infrastructure.llm_provider import ILLMProvider
from src.models.embedding import EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository


class EmbeddingService:
    def __init__(
        self, llm_provider: ILLMProvider, embedding_repo: EmbeddingRepository, tenant_id: uuid.UUID
    ):
        self.llm_provider = llm_provider
        self.embedding_repo = embedding_repo
        self.tenant_id = tenant_id

    async def process_user_identity(
        self, user_id: uuid.UUID, bio: str | None, skills: list[str]
    ) -> None:
        """
        Génère et sauvegarde le vecteur d'IDENTITÉ d'un utilisateur.
        À appeler quand l'utilisateur met à jour son profil NestJS.
        """
        text_to_vectorize = TextProcessor.build_identity_text(bio, skills)

        vector_data = await self.llm_provider.generate_embedding(text_to_vectorize)

        await self.embedding_repo.create(
            entity_type=EntityType.USER,
            entity_id=user_id,
            vector_data=vector_data,
            vector_purpose=VectorPurpose.IDENTITY,
            payload_metadata={"skills_count": len(skills)},
        )

    async def process_project_content(
        self, project_id: uuid.UUID, title: str, description: str | None, visibility: str = "PUBLIC"
    ) -> None:
        """
        Génère et sauvegarde le vecteur de CONTENU d'un projet.
        À appeler quand un projet est créé/édité sur NestJS.
        """
        text_to_vectorize = TextProcessor.build_content_text(title, description)

        vector_data = await self.llm_provider.generate_embedding(text_to_vectorize)

        await self.embedding_repo.create(
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            vector_data=vector_data,
            vector_purpose=VectorPurpose.CONTENT,
            payload_metadata={"visibility": visibility},
        )
