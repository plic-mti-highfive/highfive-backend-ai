"""Micro-benchmark du pipeline d'embedding (provider OpenAI mocké, vraie base pgvector).

Usage : uv run python -m scripts.bench_embeddings   (DATABASE_URI doit pointer sur une base migrée)
Mesure : appels au provider, temps de traitement des jobs, perte de mises à jour (interactions
concurrentes), latence et poids des requêtes de recommandation.
"""

import asyncio
import hashlib
import json
import random
import time
import uuid
from types import SimpleNamespace

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.nlp_processor import NLPManager
from src.infrastructure.llm.openai_provider import OpenAIProvider
from src.models.embedding import Embedding, EntityType, VectorPurpose
from src.repositories.embedding_repository import EmbeddingRepository
from src.services.matchmaking_service import MatchmakingService
from src.worker.handlers import (
    handle_project_identity,
    handle_user_identity,
    handle_user_interaction,
)

LATENCY = 0.05  # latence réseau simulée par appel provider
WORDS = "python api docker web mobile jeu données sécurité cloud graphe vision réseau".split()


def vec(text_: str) -> list[float]:
    seed = int(hashlib.md5(text_.encode()).hexdigest()[:8], 16)
    rnd = random.Random(seed)
    return [rnd.uniform(-1, 1) for _ in range(1536)]


class FakeClient:
    def __init__(self):
        self.embed_calls = 0
        self.embed_inputs = 0
        self.chat_calls = 0
        self.embeddings = SimpleNamespace(create=self._embed)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))

    async def _embed(self, input, model, **kw):  # noqa: A002
        self.embed_calls += 1
        items = input if isinstance(input, list) else [input]
        self.embed_inputs += len(items)
        await asyncio.sleep(LATENCY)
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=vec(t), index=i) for i, t in enumerate(items)]
        )

    async def _chat(self, **kw):
        self.chat_calls += 1
        await asyncio.sleep(LATENCY)
        msg = SimpleNamespace(content=json.dumps({"theme": "Informatique", "sub_themes": ["a"]}))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def text_of(i: int, rev: int = 0) -> str:
    rnd = random.Random(i * 7 + rev)
    return "<p>" + " ".join(rnd.choice(WORDS) + str(rnd.randint(0, 99)) for _ in range(40)) + "</p>"


async def run_jobs(sm, fn, jobs, provider, concurrency=5):
    sem = asyncio.Semaphore(concurrency)

    async def one(data):
        async with sem, sm() as s:
            await fn(data, s, provider)
            await s.commit()

    t0 = time.perf_counter()
    res = await asyncio.gather(*(one(d) for d in jobs), return_exceptions=True)
    run_jobs.errors = sum(isinstance(r, Exception) for r in res)
    return time.perf_counter() - t0


async def main():
    NLPManager.load_resources()
    engine = create_async_engine(settings.DATABASE_URI, echo=False, pool_size=10)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    tenant = uuid.uuid4()
    client = FakeClient()
    provider = OpenAIProvider()
    provider.client = client

    users = [uuid.uuid4() for _ in range(60)]
    projects = [uuid.uuid4() for _ in range(30)]

    def user_job(i, rev=0):
        return {
            "tenant_id": str(tenant),
            "user_id": str(users[i]),
            "payload": {"bio": text_of(i, rev), "skills": ["Python", "Docker"]},
        }

    def project_job(i, rev=0):
        return {
            "tenant_id": str(tenant),
            "project_id": str(projects[i]),
            "payload": {"name": f"P{i}", "description": text_of(i + 1000, rev), "tags": ["web"]},
        }

    phases = [
        ("1. création (60 users + 30 projets)", [0, 0]),
        ("2. rejeu identique (texte inchangé)", [0, 0]),
        ("3. 10 users + 5 projets modifiés, reste identique", [1, 1]),
    ]
    print(f"{'phase':55} {'appels embed':>12} {'inputs':>7} {'appels chat':>11} {'temps s':>8}")
    for name, (ur, pr) in phases:
        client.embed_calls = client.embed_inputs = client.chat_calls = 0
        uj = [user_job(i, ur if i < 10 else 0) for i in range(60)]
        pj = [project_job(i, pr if i < 5 else 0) for i in range(30)]
        t = await run_jobs(sm, handle_user_identity, uj, provider)
        t += await run_jobs(sm, handle_project_identity, pj, provider)
        print(
            f"{name:55} {client.embed_calls:>12} {client.embed_inputs:>7} "
            f"{client.chat_calls:>11} {t:>8.2f}"
        )

    # Interactions concurrentes sur un même utilisateur (perte de mises à jour ?)
    n = 40
    jobs = [
        {
            "tenant_id": str(tenant),
            "user_id": str(users[0]),
            "project_id": str(projects[i % 30]),
            "interaction_type": "LIKE",
        }
        for i in range(n)
    ]
    t = await run_jobs(sm, handle_user_interaction, jobs, provider, concurrency=8)
    async with sm() as s:
        cnt = (
            await s.execute(
                select(Embedding.payload_metadata["interactions_count"].astext).where(
                    Embedding.entity_id == users[0], Embedding.vector_purpose == VectorPurpose.INTEREST
                )
            )
        ).scalars().all()
        rows = (
            await s.execute(
                select(func.count()).where(
                    Embedding.entity_id == users[0], Embedding.vector_purpose == VectorPurpose.INTEREST
                )
            )
        ).scalar()
    print(f"\n{n} LIKE concurrents : interactions_count={cnt} (attendu {n}), lignes INTEREST={rows}, jobs en erreur={run_jobs.errors}, {t:.2f}s")

    # Recommandations : 3000 projets de plus
    async with sm() as s:
        await s.execute(
            text(
                "INSERT INTO embeddings (id, tenant_id, entity_type, entity_id, vector_purpose,"
                " vector_data, payload_metadata) SELECT gen_random_uuid(), :t, 'PROJECT',"
                " gen_random_uuid(), 'IDENTITY', (SELECT array_agg(random())::vector(1536) FROM"
                " generate_series(1,1536) WHERE g.i = g.i), '{\"theme\":\"x\"}'::jsonb"
                " FROM generate_series(1,3000) AS g(i)"
            ),
            {"t": str(tenant)},
        )
        await s.commit()
        await s.execute(text("ANALYZE embeddings"))
    async with sm() as s:
        svc = MatchmakingService(EmbeddingRepository(s, tenant))
        t0 = time.perf_counter()
        for _ in range(30):
            res = await svc.get_project_recommendations_for_user(users[1], limit=10)
        print(f"30 reco projets/user (3000 projets) : {(time.perf_counter() - t0) / 30 * 1000:.1f} ms/req, {len(res)} résultats")
        t0 = time.perf_counter()
        for _ in range(30):
            await svc.get_trending_projects(limit=10)
        print(f"30 trending : {(time.perf_counter() - t0) / 30 * 1000:.1f} ms/req")
    t0 = time.perf_counter()
    for i in range(30):
        NLPManager.normalize_text(text_of(i))
    print(f"spaCy normalize_text : {(time.perf_counter() - t0) / 30 * 1000:.1f} ms/appel")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
