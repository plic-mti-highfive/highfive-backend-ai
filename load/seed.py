"""Seed pour le test de charge : précharge utilisateurs, projets, interactions et likes.

    uv run python -m load.seed --users 2000 --projects 500

Passe par les vrais handlers du worker (spaCy, hash de contenu, upsert) avec le provider factice,
donc sans file ni réseau. Écrit `load/seed_data.json` (ids + tenant) lu par `locustfile.py`.
"""

import argparse
import asyncio
import json
import random
import uuid
from pathlib import Path

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from load.topics import TOPICS
from scripts.fake_provider import FakeLLMProvider
from src.core.config import settings
from src.core.nlp_processor import NLPManager
from src.worker.handlers import (
    handle_project_identity,
    handle_project_stats_updated,
    handle_user_identity,
    handle_user_interaction,
)

OUT = Path(__file__).with_name("seed_data.json")
fake = Faker("fr_FR")


def sentence(topic: str, n: int, rnd: random.Random) -> str:
    words = TOPICS[topic]
    return " ".join(rnd.choice(words) for _ in range(n)) + ". " + fake.sentence(nb_words=6)


async def run_batch(session_maker, provider, items, handler, concurrency):
    sem = asyncio.Semaphore(concurrency)

    async def one(data):
        async with sem, session_maker() as session:
            await handler(data, session, provider)
            await session.commit()

    await asyncio.gather(*(one(d) for d in items))


async def main(users: int, projects: int, interactions: float, seed: int) -> None:
    rnd = random.Random(seed)
    NLPManager.load_resources()
    engine = create_async_engine(settings.DATABASE_URI, pool_size=10, max_overflow=0)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    provider = FakeLLMProvider()
    tenant = str(uuid.uuid4())
    topics = list(TOPICS)

    project_ids = [str(uuid.uuid4()) for _ in range(projects)]
    user_ids = [str(uuid.uuid4()) for _ in range(users)]

    print(f"seed : {projects} projets, {users} utilisateurs (tenant {tenant})")
    await run_batch(
        session_maker,
        provider,
        [
            {
                "tenant_id": tenant,
                "project_id": pid,
                "payload": {
                    "name": f"Projet {i} " + sentence(t := rnd.choice(topics), 3, rnd),
                    "description": sentence(t, 25, rnd),
                    "tags": rnd.sample(TOPICS[t], 3),
                    "visibility": "PUBLIC",
                },
            }
            for i, pid in enumerate(project_ids)
        ],
        handle_project_identity,
        8,
    )
    await run_batch(
        session_maker,
        provider,
        [
            {
                "tenant_id": tenant,
                "user_id": uid,
                "payload": {
                    "bio": sentence(t := rnd.choice(topics), 15, rnd),
                    "skills": rnd.sample(TOPICS[t], 3),
                },
            }
            for uid in user_ids
        ],
        handle_user_identity,
        8,
    )

    # interactions : une fraction des utilisateurs a déjà un vecteur INTEREST (2 interactions)
    active = rnd.sample(user_ids, int(users * interactions))
    for _ in range(2):
        await run_batch(
            session_maker,
            provider,
            [
                {
                    "tenant_id": tenant,
                    "user_id": uid,
                    "project_id": rnd.choice(project_ids),
                    "interaction_type": rnd.choice(["LIKE", "APPLY"]),
                }
                for uid in active
            ],
            handle_user_interaction,
            8,
        )
    # compteurs de likes (alimente le trending)
    await run_batch(
        session_maker,
        provider,
        [
            {"tenant_id": tenant, "project_id": pid, "likes": int(rnd.paretovariate(1.2))}
            for pid in project_ids
        ],
        handle_project_stats_updated,
        8,
    )
    await engine.dispose()

    OUT.write_text(
        json.dumps(
            {
                "tenant_id": tenant,
                "user_ids": user_ids,
                "project_ids": project_ids,
                "topics": topics,
            }
        )
    )
    print(f"ok -> {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=2000)
    ap.add_argument("--projects", type=int, default=500)
    ap.add_argument("--active-ratio", type=float, default=0.4)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    asyncio.run(main(a.users, a.projects, a.active_ratio, a.seed))
