"""Provider LLM/embedding déterministe et sans réseau (tests, seed, charge).

L'embedding est un « sac de mots haché » normalisé sur 1536 dimensions : deux textes qui
partagent des mots ont une similarité cosinus élevée, ce qui permet de tester un vrai classement.
"""

import asyncio
import hashlib
import math
import re

DIM = 1536

THEMES = {
    "WEB": ("web", "react", "frontend", "api", "javascript", "site", "navigateur"),
    "DATA": ("données", "python", "machine", "learning", "analyse", "statistique", "modèle"),
    "SECURITY": ("sécurité", "cryptographie", "pentest", "vulnérabilité", "réseau", "audit"),
    "GAMING": ("jeu", "unity", "gameplay", "console", "joueur", "niveau"),
}


def fake_vector(text: str) -> list[float]:
    vec = [0.0] * DIM
    for word in re.findall(r"\w+", text.lower()):
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        vec[h % DIM] += 1.0
        vec[(h >> 20) % DIM] += 0.5
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        vec[0] = 1.0
        return vec
    return [v / norm for v in vec]


class FakeLLMProvider:
    """Implémente `ILLMProvider` ; `latency` simule le réseau, `calls` compte les appels."""

    def __init__(self, latency: float = 0.0):
        self.latency = latency
        self.embed_calls = 0
        self.metadata_calls = 0

    async def generate_embedding(self, text: str) -> list[float]:
        self.embed_calls += 1
        if self.latency:
            await asyncio.sleep(self.latency)
        return fake_vector(text)

    async def extract_metadata(self, text: str) -> dict:
        self.metadata_calls += 1
        if self.latency:
            await asyncio.sleep(self.latency)
        low = text.lower()
        best = max(THEMES, key=lambda t: sum(w in low for w in THEMES[t]))
        return {"theme": best, "sub_themes": [w for w in THEMES[best] if w in low][:3]}
