"""Endpoints /matchmaking : vraie base pgvector, vrais handlers, provider factice, vrai JWT."""

import uuid

import pytest

from src.core.constants import InteractionType
from src.models.embedding import VectorPurpose
from src.worker.handlers import (
    handle_project_stats_updated,
    handle_user_interaction,
)
from tests.conftest import TestingSessionLocal
from tests.integration.conftest import make_token

WEB = ("Site web React", "Application web frontend avec react et api javascript", ["web"])
DATA = ("Analyse de données", "Modèle de machine learning python pour analyse de données", ["ml"])
SEC = ("Audit sécurité", "Pentest et cryptographie : audit de sécurité réseau", ["sec"])


@pytest.fixture()
async def world(seeder):
    """3 projets de thèmes différents + 2 utilisateurs (web / données)."""
    p_web = await seeder.project(*WEB)
    p_data = await seeder.project(*DATA)
    p_sec = await seeder.project(*SEC)
    u_web = await seeder.user("Développeur web react et api javascript", ["react", "web"])
    u_data = await seeder.user("Data scientist machine learning python", ["python", "données"])
    return {"p_web": p_web, "p_data": p_data, "p_sec": p_sec, "u_web": u_web, "u_data": u_data}


def ids(resp):
    return [item["id"] for item in resp.json()]


async def test_recommendations_are_ranked_by_similarity(client, auth_headers, world):
    r = await client.get(f"/api/v1/matchmaking/users/{world['u_web']}/projects", headers=auth_headers)
    assert r.status_code == 200
    assert ids(r)[0] == str(world["p_web"])
    assert [i["position"] for i in r.json()] == [0, 1, 2]
    assert set(ids(r)) == {str(world[k]) for k in ("p_web", "p_data", "p_sec")}

    r = await client.get(
        f"/api/v1/matchmaking/users/{world['u_data']}/projects", headers=auth_headers
    )
    assert ids(r)[0] == str(world["p_data"])


async def test_recommendation_items_expose_metadata_without_vector(client, auth_headers, world):
    r = await client.get(f"/api/v1/matchmaking/users/{world['u_web']}/projects", headers=auth_headers)
    item = r.json()[0]
    assert set(item) == {"id", "position", "metadata"}
    assert item["metadata"]["theme"] == "WEB"
    assert item["metadata"]["visibility"] == "PUBLIC"


async def test_limit_is_respected(client, auth_headers, world):
    r = await client.get(
        f"/api/v1/matchmaking/users/{world['u_web']}/projects?limit=2", headers=auth_headers
    )
    assert len(r.json()) == 2


@pytest.mark.parametrize("limit", ["0", "-1", "abc", "501"])
async def test_invalid_limit_is_rejected_not_a_server_error(client, auth_headers, world, limit):
    r = await client.get(
        f"/api/v1/matchmaking/users/{world['u_web']}/projects?limit={limit}", headers=auth_headers
    )
    assert r.status_code == 422


async def test_tags_filter_on_theme(client, auth_headers, world):
    r = await client.get(
        f"/api/v1/matchmaking/users/{world['u_web']}/projects?tags=DATA", headers=auth_headers
    )
    assert ids(r) == [str(world["p_data"])]
    r = await client.get(
        f"/api/v1/matchmaking/users/{world['u_web']}/projects?tags=DATA&tags=SECURITY",
        headers=auth_headers,
    )
    assert set(ids(r)) == {str(world["p_data"]), str(world["p_sec"])}
    r = await client.get(
        f"/api/v1/matchmaking/users/{world['u_web']}/projects?tags=INEXISTANT", headers=auth_headers
    )
    assert r.json() == []


async def test_unknown_user_falls_back_to_trending(client, auth_headers, world):
    r = await client.get(f"/api/v1/matchmaking/users/{uuid.uuid4()}/projects", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 3


async def test_interactions_shift_recommendations(client, auth_headers, seeder, fake_provider, world):
    """Des APPLY répétés sur un projet sécurité font monter ce projet pour l'utilisateur web."""
    async def rank():
        r = await client.get(
            f"/api/v1/matchmaking/users/{world['u_web']}/projects", headers=auth_headers
        )
        return ids(r).index(str(world["p_sec"]))

    before = await rank()
    for _ in range(6):
        async with TestingSessionLocal() as s:
            await handle_user_interaction(
                {
                    "tenant_id": str(seeder.tenant_id),
                    "user_id": str(world["u_web"]),
                    "project_id": str(world["p_sec"]),
                    "interaction_type": InteractionType.APPLY.value,
                },
                s,
                fake_provider,
            )
            await s.commit()
    assert await rank() < before


async def test_tenant_isolation(client, world):
    other = {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}
    r = await client.get(f"/api/v1/matchmaking/users/{world['u_web']}/projects", headers=other)
    assert r.status_code == 200 and r.json() == []
    r = await client.get(f"/api/v1/matchmaking/projects/{world['p_web']}/users", headers=other)
    assert r.json() == []
    r = await client.get("/api/v1/matchmaking/trending", headers=other)
    assert r.json() == []


async def test_users_for_project_ranked_and_filtered_by_similarity(client, auth_headers, world):
    r = await client.get(f"/api/v1/matchmaking/projects/{world['p_web']}/users", headers=auth_headers)
    assert r.status_code == 200
    assert ids(r)[0] == str(world["u_web"])
    assert str(world["u_data"]) not in ids(r)  # sous le seuil de similarité (distance < 0.5)


async def test_users_for_unknown_project_is_empty(client, auth_headers, world):
    r = await client.get(f"/api/v1/matchmaking/projects/{uuid.uuid4()}/users", headers=auth_headers)
    assert r.status_code == 200 and r.json() == []


async def test_trending_orders_by_likes_and_limit(client, auth_headers, seeder, fake_provider, world):
    for project, likes in ((world["p_sec"], 500), (world["p_data"], 20)):
        async with TestingSessionLocal() as s:
            await handle_project_stats_updated(
                {"tenant_id": str(seeder.tenant_id), "project_id": str(project), "likes": likes},
                s,
                fake_provider,
            )
            await s.commit()
    r = await client.get("/api/v1/matchmaking/trending", headers=auth_headers)
    assert ids(r) == [str(world["p_sec"]), str(world["p_data"]), str(world["p_web"])]
    assert r.json()[0]["metadata"]["likes"] == 500
    r = await client.get("/api/v1/matchmaking/trending?limit=1", headers=auth_headers)
    assert ids(r) == [str(world["p_sec"])]


async def test_trending_excludes_users(client, auth_headers, world):
    r = await client.get("/api/v1/matchmaking/trending", headers=auth_headers)
    assert str(world["u_web"]) not in ids(r)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/matchmaking/trending",
        f"/api/v1/matchmaking/users/{uuid.uuid4()}/projects",
        f"/api/v1/matchmaking/projects/{uuid.uuid4()}/users",
    ],
)
async def test_auth_required(client, path):
    assert (await client.get(path)).status_code in (401, 403)
    bad = await client.get(path, headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401
    no_tenant = await client.get(
        path, headers={"Authorization": f"Bearer {make_token('x')}"}
    )
    assert no_tenant.status_code == 401  # tenantId invalide


async def test_token_without_tenant_is_rejected(client):
    import jwt

    from src.core.config import settings

    tok = jwt.encode({"sub": "u"}, settings.JWT_SECRET, algorithm="HS256")
    r = await client.get("/api/v1/matchmaking/trending", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


async def test_invalid_uuid_in_path_is_422(client, auth_headers):
    r = await client.get("/api/v1/matchmaking/users/pas-un-uuid/projects", headers=auth_headers)
    assert r.status_code == 422


async def test_identity_vectors_exist_after_seed(world, seeder):
    from sqlalchemy import select

    from src.models.embedding import Embedding

    async with TestingSessionLocal() as s:
        rows = (
            await s.execute(
                select(Embedding.entity_id).where(
                    Embedding.tenant_id == seeder.tenant_id,
                    Embedding.vector_purpose == VectorPurpose.IDENTITY,
                )
            )
        ).all()
    assert len(rows) == 5
