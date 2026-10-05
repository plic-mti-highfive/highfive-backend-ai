import asyncio
import json

from openai import AsyncOpenAI

import src.core.config as config
from src.core.constants import EMBEDDING_MODEL, FALLBACK_THEME
from src.core.logger import get_logger
from src.infrastructure.llm.embedding_batcher import EmbeddingBatcher, LRUCache, text_key
from src.infrastructure.llm_provider import ILLMProvider

logger = get_logger(__name__)

METADATA_PROMPT = """
        Analyse le texte suivant et extrais les catégories.
        Réponds UNIQUEMENT avec un objet JSON valide contenant :
        - "theme": Le thème global principal (ex: "Jeux Vidéo", "Art", "Informatique", "Musique").
        - "sub_themes": Une liste de 2 à 3 sous-catégories ultra-précises
          (ex: ["Platformer 2D", "Peinture à l'huile"]).

        Texte à analyser :
        """


class OpenAIProvider(ILLMProvider):
    def __init__(self):
        # timeout explicite : un appel bloqué ne doit pas immobiliser un slot du worker
        self.client = AsyncOpenAI(
            api_key=config.settings.OPENAI_API_KEY, timeout=30.0, max_retries=3
        )
        self.embedding_model = EMBEDDING_MODEL
        self.chat_model = "gpt-4o-mini"
        self._embedding_batcher = EmbeddingBatcher(self._embed_batch, namespace=EMBEDDING_MODEL)
        self._metadata_cache: LRUCache[dict] = LRUCache(512)

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Un seul appel API pour tout le lot."""
        try:
            response = await self.client.embeddings.create(input=texts, model=self.embedding_model)
        except Exception as e:
            raise Exception(f"OpenAI Error: {str(e)}")
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    async def generate_embedding(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty or whitespace.")
        # Regroupé avec les autres demandes concurrentes, mis en cache par contenu
        return await self._embedding_batcher.embed(text)

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Version liste : les textes partent dans le même appel provider (batching)."""
        return list(await asyncio.gather(*(self.generate_embedding(t) for t in texts)))

    async def extract_metadata(self, text: str) -> dict:
        if not text:
            return {"theme": FALLBACK_THEME, "sub_themes": []}

        key = text_key(self.chat_model, text)
        cached = self._metadata_cache.get(key)
        if cached is not None:
            return dict(cached)

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                response_format={"type": "json_object"},
                temperature=0,  # classification reproductible (et donc cacheable)
                messages=[
                    {"role": "system", "content": "Tu es un classificateur de données expert."},
                    {"role": "user", "content": f"{METADATA_PROMPT}\n{text}"},
                ],
            )
            metadata = json.loads(response.choices[0].message.content)
            if not isinstance(metadata, dict):
                raise ValueError("metadata is not a JSON object")
        except Exception as e:
            logger.warning(f"Metadata extraction failed, using fallback: {e}")
            return {"theme": FALLBACK_THEME, "sub_themes": []}

        self._metadata_cache.put(key, metadata)
        return dict(metadata)
