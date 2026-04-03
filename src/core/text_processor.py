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
    def build_identity_text(bio: str | None, skills: list[str]) -> str:
        """Builds the semantic text for a user profile (IDENTITY)."""
        clean_bio = TextProcessor.clean_html(bio)
        parts = ["Profil étudiant."]
        if clean_bio:
            parts.append(f"Biographie : {clean_bio}")
        if skills:
            parts.append(f"Compétences maîtrisées : {', '.join(skills)}.")
        return " ".join(parts)

    @staticmethod
    def build_content_text(title: str, description: str | None) -> str:
        """Builds the semantic text for a project or ticket (CONTENT)."""
        clean_title = TextProcessor.clean_html(title)
        clean_desc = TextProcessor.clean_html(description)

        parts = [f"Titre : {clean_title}."]
        if clean_desc:
            parts.append(f"Description : {clean_desc}")
        return " ".join(parts)
