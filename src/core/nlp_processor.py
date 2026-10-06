import asyncio
import re
from concurrent.futures import ThreadPoolExecutor

import spacy

from src.core.logger import get_logger

logger = get_logger(__name__)


class NLPManager:
    """
    Singleton managing NLP resources.
    """

    _nlp = None
    # Un seul thread dédié : spaCy est CPU-bound, on libère la boucle d'événements sans
    # sur-souscrire les CPU (to_thread en parallèle était ~20x plus lent par appel).
    _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nlp")

    @classmethod
    def load_resources(cls) -> None:
        """
        Load NLP resources into memory. Should be called once at application startup.
        """
        if cls._nlp is None:
            logger.info("Loading spaCy NLP model 'fr_core_news_sm' into memory...")
            # Le parser et le NER ne servent pas (lemmes + stop words uniquement) : ~2,5x plus
            # rapide, sortie identique.
            cls._nlp = spacy.load("fr_core_news_sm", exclude=["parser", "ner"])
            logger.info("NLP model loaded successfully.")

    @classmethod
    def get_nlp(cls):
        if cls._nlp is None:
            raise RuntimeError("NLPManager not initialized. Call load_resources() at startup.")
        return cls._nlp

    @staticmethod
    def clean_html(raw_text: str | None) -> str:
        if not raw_text:
            return ""
        clean_text = re.sub(r"<[^>]+>", " ", raw_text)
        clean_text = re.sub(r"\s+", " ", clean_text)
        return clean_text.strip()

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Normalize text by lemmatizing and removing stop words, punctuation, and extra spaces.
            - Lemmatization: Convert words to their base form (e.g., "running" -> "run").
            - Stop word removal: Remove common words that do not add much meaning
              (e.g., "the", "and").
            - Punctuation removal: Remove punctuation characters.
            - Space normalization: Replace multiple spaces with a single space and trim
              leading/trailing spaces.
        This helps in creating cleaner and more consistent text for embedding generation.
        """
        if not text:
            return ""

        clean_text = cls.clean_html(text)

        nlp = cls.get_nlp()
        doc = nlp(clean_text)

        tokens = [
            token.lemma_.lower()
            for token in doc
            if not token.is_stop and not token.is_punct and not token.is_space
        ]

        return " ".join(tokens)

    @staticmethod
    def build_text_from_schema(payload: dict, schema_mapping: dict) -> str:
        """Construit une chaîne sémantique propre à partir d'un payload."""
        parts = []
        for key, template in schema_mapping.items():
            value = payload.get(key)
            if value:
                if isinstance(value, list):
                    value = " ".join(str(v) for v in value)

                if isinstance(value, str):
                    value = NLPManager.normalize_text(value)

                parts.append(template.format(value))

        return " ".join(parts)

    @classmethod
    async def build_text_from_schema_async(cls, payload: dict, schema_mapping: dict) -> str:
        """Même chose que build_text_from_schema, sans bloquer la boucle d'événements."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            cls._executor, cls.build_text_from_schema, payload, schema_mapping
        )
