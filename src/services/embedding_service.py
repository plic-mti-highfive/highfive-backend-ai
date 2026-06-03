import asyncio
import math
import uuid

from sqlalchemy.orm.attributes import flag_modified

from src.core.constants import INTERACTION_WEIGHTS, InteractionType
from src.core.logger import get_logger
from src.core.nlp_processor import NLPManager
from src.infrastructure.llm_provider import ILLMProvider
from src.models.embedding import EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository

logger = get_logger(__name__)

# ----- VECTOR SCHEMAS -----
# USER
USER_IDENTITY_SCHEMA = {
    "bio": "Biographie : {}.",
    "skills": "Compétences : {}.",
}

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

    @staticmethod
    def _calculate_ema_vector(
        current_vector: list[float], target_vector: list[float], weight: float
    ) -> list[float]:
        """
        Calcule la moyenne mobile pondérée et re-normalise le vecteur.
        """
        # 1. Calcul de la moyenne pondérée (EMA)
        new_vector = [
            (curr * (1.0 - weight)) + (targ * weight)
            for curr, targ in zip(current_vector, target_vector)
        ]

        # 2. Re-normalisation
        magnitude = math.sqrt(sum(v**2 for v in new_vector))
        if magnitude == 0:
            return current_vector

        return [v / magnitude for v in new_vector]

    async def process_user_interaction(
        self, user_id: uuid.UUID, project_id: uuid.UUID, interaction_type: InteractionType
    ) -> None:
        """
        Met à jour le vecteur d'INTEREST de l'utilisateur suite à une interaction.
        """
        logger.info(f"Processing {interaction_type} for user {user_id} on project {project_id}")

        # 1. Récupérer le vecteur du Projet
        project_emb = await self.embedding_repo.get_by_entity_and_purpose(
            entity_id=project_id, purpose=VectorPurpose.IDENTITY
        )
        if not project_emb:
            raise ValueError(f"Project {project_id} vector not found. Retrying later...")

        # 2. Récupérer le vecteur d'Intérêt actuel de l'User
        user_interest_emb = await self.embedding_repo.get_by_entity_and_purpose(
            entity_id=user_id, purpose=VectorPurpose.INTEREST
        )

        # COLD START : On récupère le vecteur d'IDENTITÉ
        if not user_interest_emb:
            user_identity_emb = await self.embedding_repo.get_by_entity_and_purpose(
                entity_id=user_id, purpose=VectorPurpose.IDENTITY
            )
            if not user_identity_emb:
                logger.warning(f"User {user_id} has no identity vector. Cannot init interest.")
                return

            logger.info("Initializing new INTEREST vector from IDENTITY vector.")
            user_interest_emb = await self.embedding_repo.create(
                entity_type=EntityType.USER,
                entity_id=user_id,
                vector_data=user_identity_emb.vector_data,
                vector_purpose=VectorPurpose.INTEREST,
                payload_metadata={"interactions_count": 0},
            )

        # 3. Appliquer la formule mathématique (Mean Pooling)
        weight = INTERACTION_WEIGHTS[interaction_type]
        new_vector = self._calculate_ema_vector(
            current_vector=user_interest_emb.vector_data,
            target_vector=project_emb.vector_data,
            weight=weight,
        )

        user_interest_emb.vector_data = new_vector

        current_count = user_interest_emb.payload_metadata.get("interactions_count", 0)
        user_interest_emb.payload_metadata["interactions_count"] = current_count + 1

        flag_modified(user_interest_emb, "payload_metadata")

        await self.embedding_repo.db.commit()
        logger.info(f"User {user_id} interest vector successfully moved by {weight * 100}%.")

    async def process_user_identity(
        self,
        user_id: uuid.UUID,
        payload: dict,
    ) -> None:
        """
        Génère et sauvegarde le vecteur d'IDENTITÉ d'un utilisateur.
        À appeler quand l'utilisateur met à jour son profil NestJS.
        """
        logger.info(f"Processing user identity vector for user {user_id}")
        text_to_vectorize = NLPManager.build_text_from_schema(payload, USER_IDENTITY_SCHEMA)
        logger.debug(f"Text prepared for vectorization (length: {len(text_to_vectorize)} chars)")

        vector_data = await self.llm_provider.generate_embedding(text_to_vectorize)
        logger.debug(f"Embedding generated for user {user_id}")

        await self.embedding_repo.create(
            entity_type=EntityType.USER,
            entity_id=user_id,
            vector_data=vector_data,
            vector_purpose=VectorPurpose.IDENTITY,
            payload_metadata={"skills_count": len(payload.get("skills", []))},
        )
        logger.info(f"User identity vector saved successfully for user {user_id}")

    async def process_project_identity(
        self,
        project_id: uuid.UUID,
        payload: dict,
    ) -> None:
        logger.info(f"Processing project identity vector for project {project_id}")
        text_to_vectorize = NLPManager.build_text_from_schema(payload, PROJECT_IDENTITY_SCHEMA)
        logger.debug(f"Text prepared for vectorization (length: {len(text_to_vectorize)} chars)")

        vector_task = self.llm_provider.generate_embedding(text_to_vectorize)
        metadata_task = self.llm_provider.extract_metadata(text_to_vectorize)
        logger.debug(
            "Started parallel embedding generation and metadata extraction "
            f"for project {project_id}"
        )

        vector_data, extracted_meta = await asyncio.gather(vector_task, metadata_task)
        logger.debug(f"Embedding and metadata completed for project {project_id}")

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
        logger.info(f"Project identity vector saved successfully for project {project_id}")
