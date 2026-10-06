import asyncio
import hashlib
import json
import math
import uuid

from src.core.constants import (
    EMBEDDING_MODEL,
    FALLBACK_THEME,
    INTERACTION_WEIGHTS,
    TEXT_PIPELINE_VERSION,
    InteractionType,
)
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


def compute_content_hash(payload: dict, schema: dict) -> str:
    """
    Hash stable du contenu source qui détermine l'embedding : champs du schéma, modèle et version
    du pipeline. Si le hash n'a pas changé, inutile de relancer spaCy ni le provider.
    """
    relevant = {key: payload.get(key) for key in schema}
    raw = json.dumps(
        {"model": EMBEDDING_MODEL, "v": TEXT_PIPELINE_VERSION, "data": relevant},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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

        La ligne INTEREST est verrouillée (FOR UPDATE) le temps du calcul : deux interactions
        concurrentes s'enchaînent au lieu de s'écraser.
        """
        logger.info(f"Processing {interaction_type} for user {user_id} on project {project_id}")

        # 1. Vecteurs d'identité du projet et de l'utilisateur en une seule requête
        identities = await self.embedding_repo.get_many(
            [project_id, user_id], [VectorPurpose.IDENTITY]
        )
        project_emb = identities.get((project_id, VectorPurpose.IDENTITY))
        if not project_emb:
            raise ValueError(f"Project {project_id} vector not found. Retrying later...")

        # 2. Vecteur d'intérêt actuel (verrouillé)
        user_interest_emb = await self.embedding_repo.get_for_update(
            user_id, VectorPurpose.INTEREST
        )

        # COLD START : on initialise depuis le vecteur d'IDENTITÉ
        if not user_interest_emb:
            user_identity_emb = identities.get((user_id, VectorPurpose.IDENTITY))
            if not user_identity_emb:
                logger.warning(f"User {user_id} has no identity vector. Cannot init interest.")
                return

            logger.info("Initializing new INTEREST vector from IDENTITY vector.")
            await self.embedding_repo.insert_if_absent(
                entity_type=EntityType.USER,
                entity_id=user_id,
                vector_data=user_identity_emb.vector_data,
                vector_purpose=VectorPurpose.INTEREST,
                payload_metadata={"interactions_count": 0},
            )
            user_interest_emb = await self.embedding_repo.get_for_update(
                user_id, VectorPurpose.INTEREST
            )

        # 3. Formule mathématique (moyenne mobile pondérée)
        weight = INTERACTION_WEIGHTS[interaction_type]
        user_interest_emb.vector_data = self._calculate_ema_vector(
            current_vector=list(user_interest_emb.vector_data),
            target_vector=list(project_emb.vector_data),
            weight=weight,
        )

        metadata = dict(user_interest_emb.payload_metadata or {})
        metadata["interactions_count"] = metadata.get("interactions_count", 0) + 1
        user_interest_emb.payload_metadata = metadata  # nouvel objet : détecté par SQLAlchemy

        await self.embedding_repo.db.flush()
        logger.info(f"User {user_id} interest vector successfully moved by {weight * 100}%.")

    async def _build_text(self, payload: dict, schema: dict) -> str:
        return await NLPManager.build_text_from_schema_async(payload, schema)

    async def process_user_identity(
        self,
        user_id: uuid.UUID,
        payload: dict,
    ) -> None:
        """
        Génère et sauvegarde le vecteur d'IDENTITÉ d'un utilisateur.
        À appeler quand l'utilisateur met à jour son profil NestJS.
        Ne fait rien si le contenu source n'a pas changé depuis le dernier calcul.
        """
        logger.info(f"Processing user identity vector for user {user_id}")
        content_hash = compute_content_hash(payload, USER_IDENTITY_SCHEMA)
        stored_hash = await self.embedding_repo.get_content_hash(user_id, VectorPurpose.IDENTITY)
        if stored_hash == content_hash:
            logger.info(f"User identity unchanged for user {user_id}, embedding skipped")
            return

        text_to_vectorize = await self._build_text(payload, USER_IDENTITY_SCHEMA)
        if not text_to_vectorize.strip():
            logger.warning(f"Empty identity text for user {user_id}, nothing to vectorize")
            return
        logger.debug(f"Text prepared for vectorization (length: {len(text_to_vectorize)} chars)")

        vector_data = await self.llm_provider.generate_embedding(text_to_vectorize)
        logger.debug(f"Embedding generated for user {user_id}")

        await self.embedding_repo.upsert(
            entity_type=EntityType.USER,
            entity_id=user_id,
            vector_data=vector_data,
            vector_purpose=VectorPurpose.IDENTITY,
            payload_metadata={"skills_count": len(payload.get("skills") or [])},
            content_hash=content_hash,
        )
        logger.info(f"User identity vector saved for user {user_id}")

    async def process_project_identity(
        self,
        project_id: uuid.UUID,
        payload: dict,
    ) -> None:
        """
        Génère et sauvegarde le vecteur d'IDENTITÉ d'un projet (+ métadonnées thématiques).
        Si le texte source n'a pas changé, seules les métadonnées légères (visibility) sont
        rafraîchies : ni spaCy, ni embedding, ni extraction LLM.
        """
        logger.info(f"Processing project identity vector for project {project_id}")
        visibility = payload.get("visibility", "PUBLIC")
        content_hash = compute_content_hash(payload, PROJECT_IDENTITY_SCHEMA)
        stored_hash = await self.embedding_repo.get_content_hash(project_id, VectorPurpose.IDENTITY)
        if stored_hash == content_hash:
            await self.embedding_repo.patch_metadata(
                project_id, VectorPurpose.IDENTITY, {"visibility": visibility}
            )
            logger.info(f"Project identity unchanged for project {project_id}, embedding skipped")
            return

        text_to_vectorize = await self._build_text(payload, PROJECT_IDENTITY_SCHEMA)
        if not text_to_vectorize.strip():
            logger.warning(f"Empty identity text for project {project_id}, nothing to vectorize")
            return
        logger.debug(f"Text prepared for vectorization (length: {len(text_to_vectorize)} chars)")

        vector_data, extracted_meta = await asyncio.gather(
            self.llm_provider.generate_embedding(text_to_vectorize),
            self.llm_provider.extract_metadata(text_to_vectorize),
        )
        logger.debug(f"Embedding and metadata completed for project {project_id}")

        final_metadata = {
            "visibility": visibility,
            "theme": extracted_meta.get("theme"),
            "sub_themes": extracted_meta.get("sub_themes", []),
        }

        # Extraction LLM en échec (repli) : on ne mémorise pas le hash, le prochain job réessaiera.
        extraction_failed = extracted_meta.get(
            "theme"
        ) == FALLBACK_THEME and not extracted_meta.get("sub_themes")

        await self.embedding_repo.upsert(
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            vector_data=vector_data,
            vector_purpose=VectorPurpose.IDENTITY,
            payload_metadata=final_metadata,
            content_hash=None if extraction_failed else content_hash,
        )
        logger.info(f"Project identity vector saved for project {project_id}")
