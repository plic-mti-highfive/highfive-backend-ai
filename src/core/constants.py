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
