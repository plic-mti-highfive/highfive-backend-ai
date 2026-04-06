import re


class TextProcessor:
    """NLP utilities for processing user bios, project descriptions, and other text content."""

    @staticmethod
    def clean_html(raw_text: str | None) -> str:
        """Supprime les balises HTML et normalise les espaces."""
        if not raw_text:
            return ""
        clean_text = re.sub(r"<[^>]+>", " ", raw_text)
        clean_text = re.sub(r"\s+", " ", clean_text)
        return clean_text.strip()

    @staticmethod
    def build_text_from_schema(payload: dict, schema_mapping: dict) -> str:
        """
        Construct a text by applying the schema mapping to the payload.
        The schema_mapping defines how to format each field in the payload into text.
        Ex: schema = {"bio": "Biographie : {}", "skills": "Compétences : {}"}
        """
        parts = []
        for key, template in schema_mapping.items():
            value = payload.get(key)
            if value:
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)

                if isinstance(value, str):
                    value = TextProcessor.clean_html(value)

                parts.append(template.format(value))
        return " ".join(parts)
