import re

import spacy

from src.core.logger import get_logger

logger = get_logger(__name__)


class NLPManager:
    """
    Singleton managing NLP resources.
    """

    _nlp = None

    @classmethod
    def load_resources(cls) -> None:
        """
        Load NLP resources into memory. Should be called once at application startup.
        """
        if cls._nlp is None:
            logger.info("Loading spaCy NLP model 'fr_core_news_sm' into memory...")
            cls._nlp = spacy.load("fr_core_news_sm")
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
