"""
Contrat Redis (docs/redis-contract.md) de bout en bout : de vrais jobs BullMQ sont poussés dans
Redis, de vrais workers (WorkerFactory + config/workers.yaml) les consomment, le résultat est lu
dans Postgres/pgvector. Seul le provider embedding/LLM est factice.
"""

import asyncio
import time
import uuid

import pytest
import pytest_asyncio
from bullmq import Queue
from sqlalchemy import func, select

from scripts.fake_provider import FakeLLMProvider
from src.core.config import settings
from src.models.embedding import Embedding, VectorPurpose
from src.worker.factory import WorkerFactory
from tests.conftest import TestingSessionLocal
from tests.integration.conftest import make_token


async def wait_for(predicate, timeout=20.0, interval=0.1):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = await predicate()
        if value:
            return value
        await asyncio.sleep(interval)
    raise AssertionError("condition non atteinte dans le délai imparti")


@pytest_asyncio.fixture()
async def queues():
    ai = Queue("ai_tasks", {"connection": settings.redis_opts})
    fast = Queue("fast_events", {"connection": settings.redis_opts})
    await ai.obliterate(force=True)
    await fast.obliterate(force=True)
    yield ai, fast
    await ai.obliterate(force=True)
    await fast.obliterate(force=True)
    await ai.close()
    await fast.close()


@pytest.fixture()
def provider():
    return FakeLLMProvider()


@pytest_asyncio.fixture()
async def workers(provider, queues):
    factory = WorkerFactory(TestingSessionLocal, provider, settings.redis_opts)
    running = factory.create_workers(settings.load_workers_config())
    yield running
    for w in running:
        await w.close(force=True)


@pytest_asyncio.fixture(autouse=True)
async def cleanup(test_tenant_id):
    yield
    from sqlalchemy import text

    async with TestingSessionLocal() as s:
        await s.execute(text("DELETE FROM embeddings WHERE tenant_id = :t"), {"t": test_tenant_id})
        await s.commit()


async def fetch(tenant_id, entity_id, purpose=VectorPurpose.IDENTITY):
    async with TestingSessionLocal() as s:
        return (
            await s.execute(
                select(Embedding).where(
                    Embedding.tenant_id == tenant_id,
                    Embedding.entity_id == entity_id,
                    Embedding.vector_purpose == purpose,
                )
            )
        ).scalar_one_or_none()


def user_job(tenant_id, user_id, bio="Développeur web react", skills=("react", "api")):
    return {
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "payload": {"bio": bio, "skills": list(skills)},
    }


def project_job(tenant_id, project_id, name="Site web", description="Application web react api"):
    return {
        "tenant_id": str(tenant_id),
        "project_id": str(project_id),
        "payload": {"name": name, "description": description, "tags": ["web"], "visibility": "PUBLIC"},
    }


# ----- contrat statique -----


def test_workers_yaml_matches_the_documented_contract():
    cfg = {w.queue: w for w in settings.load_workers_config().workers}
    assert set(cfg) == {"ai_tasks", "fast_events"}
    assert (cfg["ai_tasks"].concurrency, cfg["ai_tasks"].max_retries) == (5, 3)
    assert (cfg["ai_tasks"].retry_backoff_ms) == 1000
    assert (cfg["fast_events"].concurrency, cfg["fast_events"].max_retries) == (2, 2)
    assert (cfg["fast_events"].retry_backoff_ms) == 2000


# ----- les 4 types de jobs -----


async def test_update_user_identity_job(queues, workers, test_tenant_id):
    ai, _ = queues
    uid = uuid.uuid4()
    await ai.add("update_user_identity", user_job(test_tenant_id, uid))

    emb = await wait_for(lambda: fetch(test_tenant_id, uid))
    assert emb.payload_metadata == {"skills_count": 2}
    assert emb.content_hash and len(emb.vector_data) == 1536


async def test_update_project_identity_job(queues, workers, test_tenant_id):
    ai, _ = queues
    pid = uuid.uuid4()
    await ai.add("update_project_identity", project_job(test_tenant_id, pid))

    emb = await wait_for(lambda: fetch(test_tenant_id, pid))
    assert emb.payload_metadata["visibility"] == "PUBLIC"
    assert emb.payload_metadata["theme"] == "WEB"


async def test_identity_job_replayed_is_idempotent(queues, workers, provider, test_tenant_id):
    ai, _ = queues
    uid = uuid.uuid4()
    await ai.add("update_user_identity", user_job(test_tenant_id, uid))
    await wait_for(lambda: fetch(test_tenant_id, uid))
    await ai.add("update_user_identity", user_job(test_tenant_id, uid))
    await wait_for(lambda: _completed(ai, 2))
    assert provider.embed_calls == 1
    async with TestingSessionLocal() as s:
        n = await s.scalar(
            select(func.count()).select_from(Embedding).where(Embedding.entity_id == uid)
        )
    assert n == 1


async def _completed(queue, n):
    counts = await queue.getJobCounts("completed", "waiting", "active")
    return counts.get("waiting", 0) == 0 and counts.get("active", 0) == 0


async def test_project_stats_updated_job_keeps_identity_metadata(queues, workers, test_tenant_id):
    ai, fast = queues
    pid = uuid.uuid4()
    await ai.add("update_project_identity", project_job(test_tenant_id, pid))
    await wait_for(lambda: fetch(test_tenant_id, pid))
    await fast.add(
        "project_stats_updated",
        {"tenant_id": str(test_tenant_id), "project_id": str(pid), "likes": 42},
    )

    async def liked():
        e = await fetch(test_tenant_id, pid)
        return e if e.payload_metadata.get("likes") == 42 else None

    emb = await wait_for(liked)
    assert emb.payload_metadata["theme"] == "WEB"


async def test_user_interaction_job_creates_then_moves_interest_vector(
    queues, workers, test_tenant_id
):
    ai, fast = queues
    uid, pid = uuid.uuid4(), uuid.uuid4()
    await ai.add("update_user_identity", user_job(test_tenant_id, uid, "Passionné de jeux unity"))
    await ai.add("update_project_identity", project_job(test_tenant_id, pid, "Audit", "pentest sécurité"))
    await wait_for(lambda: fetch(test_tenant_id, pid))
    await wait_for(lambda: fetch(test_tenant_id, uid))
    identity = await fetch(test_tenant_id, uid)

    await fast.add(
        "user_interacted_with_project",
        {
            "tenant_id": str(test_tenant_id),
            "user_id": str(uid),
            "project_id": str(pid),
            "interaction_type": "APPLY",
        },
    )

    async def interest():
        return await fetch(test_tenant_id, uid, VectorPurpose.INTEREST)

    emb = await wait_for(interest)
    assert emb.payload_metadata["interactions_count"] == 1
    assert not (emb.vector_data == identity.vector_data).all()
    assert float((emb.vector_data**2).sum()) == pytest.approx(1.0, abs=1e-4)


async def test_concurrent_likes_are_all_counted(queues, workers, test_tenant_id):
    ai, fast = queues
    uid, pid = uuid.uuid4(), uuid.uuid4()
    await ai.add("update_user_identity", user_job(test_tenant_id, uid))
    await ai.add("update_project_identity", project_job(test_tenant_id, pid))
    await wait_for(lambda: fetch(test_tenant_id, pid))
    await wait_for(lambda: fetch(test_tenant_id, uid))
    for _ in range(30):
        await fast.add(
            "user_interacted_with_project",
            {
                "tenant_id": str(test_tenant_id),
                "user_id": str(uid),
                "project_id": str(pid),
                "interaction_type": "LIKE",
            },
        )

    async def all_counted():
        e = await fetch(test_tenant_id, uid, VectorPurpose.INTEREST)
        return e if e and e.payload_metadata["interactions_count"] == 30 else None

    await wait_for(all_counted, timeout=30)


# ----- cas d'erreur -----


async def test_unknown_job_name_fails_without_killing_the_worker(queues, workers, test_tenant_id):
    ai, _ = queues
    await ai.add("job_inconnu", {"tenant_id": str(test_tenant_id)})
    uid = uuid.uuid4()
    await ai.add("update_user_identity", user_job(test_tenant_id, uid))
    await wait_for(lambda: fetch(test_tenant_id, uid))

    async def failed():
        return (await ai.getJobCounts("failed")).get("failed", 0) >= 1

    await wait_for(failed)


async def test_malformed_job_does_not_block_following_jobs(queues, workers, test_tenant_id):
    ai, _ = queues
    await ai.add("update_user_identity", {"tenant_id": "pas-un-uuid", "user_id": "x"})
    uid = uuid.uuid4()
    await ai.add("update_user_identity", user_job(test_tenant_id, uid))
    await wait_for(lambda: fetch(test_tenant_id, uid))


async def test_interaction_arriving_before_identities_is_eventually_applied(
    queues, workers, test_tenant_id
):
    """
    Cas réel : le core publie l'interaction (fast_events, instantané) avant que les identités
    (ai_tasks, lent) aient été vectorisées. Le job ne doit pas être perdu : retry (workers.yaml).
    """
    ai, fast = queues
    uid, pid = uuid.uuid4(), uuid.uuid4()
    await fast.add(
        "user_interacted_with_project",
        {
            "tenant_id": str(test_tenant_id),
            "user_id": str(uid),
            "project_id": str(pid),
            "interaction_type": "LIKE",
        },
    )
    await asyncio.sleep(0.3)
    await ai.add("update_user_identity", user_job(test_tenant_id, uid))
    await ai.add("update_project_identity", project_job(test_tenant_id, pid))

    async def applied():
        e = await fetch(test_tenant_id, uid, VectorPurpose.INTEREST)
        return e if e and e.payload_metadata["interactions_count"] == 1 else None

    await wait_for(applied, timeout=15)


async def test_end_to_end_job_then_http_recommendation(queues, workers, client, test_tenant_id):
    ai, _ = queues
    uid = uuid.uuid4()
    web, sec = uuid.uuid4(), uuid.uuid4()
    await ai.add("update_project_identity", project_job(test_tenant_id, web))
    await ai.add(
        "update_project_identity",
        project_job(test_tenant_id, sec, "Audit", "pentest cryptographie sécurité réseau"),
    )
    await ai.add("update_user_identity", user_job(test_tenant_id, uid))
    await wait_for(lambda: fetch(test_tenant_id, uid))
    await wait_for(lambda: fetch(test_tenant_id, sec))
    await wait_for(lambda: fetch(test_tenant_id, web))

    r = await client.get(
        f"/api/v1/matchmaking/users/{uid}/projects",
        headers={"Authorization": f"Bearer {make_token(test_tenant_id)}"},
    )
    assert r.status_code == 200
    assert [i["id"] for i in r.json()][0] == str(web)
