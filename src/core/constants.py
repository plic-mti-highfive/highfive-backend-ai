import enum


class InteractionType(str, enum.Enum):
    LIKE = "LIKE"
    APPLY = "APPLY"


INTERACTION_WEIGHTS = {
    InteractionType.LIKE: 0.10,
    InteractionType.APPLY: 0.30,
}

OFFICIAL_THEMES = ["WEB", "MOBILE", "GAMING", "DATA", "ART_3D", "HARDWARE", "SECURITY"]

TRENDING_GRAVITY = 1.5

# Modèle d'embedding et version du pipeline de texte : entrent dans le content_hash, donc
# changer l'un des deux invalide les embeddings existants (ils seront recalculés au prochain job).
EMBEDDING_MODEL = "text-embedding-3-small"
TEXT_PIPELINE_VERSION = 1

# Thème renvoyé par le provider quand l'extraction de métadonnées échoue.
FALLBACK_THEME = "Général"
