"""Calculs vectoriels vérifiés numériquement (EMA d'intérêt, combinaison, hash de contenu)."""

import math
import uuid

import pytest

from src.core.constants import INTERACTION_WEIGHTS, InteractionType
from src.repositories.embedding_repository import EmbeddingRepository
from src.services import embedding_service
from src.services.embedding_service import (
    PROJECT_IDENTITY_SCHEMA,
    USER_IDENTITY_SCHEMA,
    EmbeddingService,
    compute_content_hash,
)
from src.services.matchmaking_service import MatchmakingService

ema = EmbeddingService._calculate_ema_vector


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def test_ema_weighted_average_then_normalised():
    # 0.9 * [1,0] + 0.1 * [0,1] = [0.9, 0.1] -> / sqrt(0.82)
    out = ema([1.0, 0.0], [0.0, 1.0], 0.1)
    n = math.sqrt(0.82)
    assert out == pytest.approx([0.9 / n, 0.1 / n])
    assert norm(out) == pytest.approx(1.0)


def test_ema_weight_zero_keeps_direction_and_weight_one_jumps_to_target():
    assert ema([0.6, 0.8], [1.0, 0.0], 0.0) == pytest.approx([0.6, 0.8])
    assert ema([0.6, 0.8], [1.0, 0.0], 1.0) == pytest.approx([1.0, 0.0])


def test_ema_apply_moves_further_than_like():
    like = ema([1.0, 0.0], [0.0, 1.0], INTERACTION_WEIGHTS[InteractionType.LIKE])
    apply = ema([1.0, 0.0], [0.0, 1.0], INTERACTION_WEIGHTS[InteractionType.APPLY])
    assert apply[1] > like[1] > 0


def test_ema_converges_toward_target_with_repeated_interactions():
    v = [1.0, 0.0]
    for _ in range(50):
        v = ema(v, [0.0, 1.0], 0.1)
    assert v[1] > 0.99


def test_ema_zero_magnitude_returns_current_vector():
    # moyenne exactement nulle : vecteurs opposés, poids 0.5
    assert ema([1.0, 0.0], [-1.0, 0.0], 0.5) == [1.0, 0.0]


def test_ema_weights_are_valid():
    assert all(0 < w <= 1 for w in INTERACTION_WEIGHTS.values())
    assert set(INTERACTION_WEIGHTS) == set(InteractionType)


def test_combine_vectors_default_weights_80_20():
    svc = MatchmakingService(embedding_repo=None)
    out = svc._combine_vectors([1.0, 0.0], [0.0, 1.0])
    n = math.sqrt(0.8**2 + 0.2**2)
    assert out == pytest.approx([0.8 / n, 0.2 / n])
    assert norm(out) == pytest.approx(1.0)


def test_combine_vectors_zero_returns_zero_vector():
    svc = MatchmakingService(embedding_repo=None)
    assert svc._combine_vectors([0.0, 0.0], [0.0, 0.0]) == [0.0, 0.0]


def test_content_hash_is_stable_and_hex_sha256():
    p = {"bio": "Salut", "skills": ["a", "b"]}
    h = compute_content_hash(p, USER_IDENTITY_SCHEMA)
    assert h == compute_content_hash(dict(p), USER_IDENTITY_SCHEMA)
    assert len(h) == 64 and int(h, 16) >= 0


def test_content_hash_ignores_fields_outside_schema_and_key_order():
    a = compute_content_hash({"name": "x", "description": "y"}, PROJECT_IDENTITY_SCHEMA)
    b = compute_content_hash(
        {"description": "y", "name": "x", "visibility": "PRIVATE", "likes": 9},
        PROJECT_IDENTITY_SCHEMA,
    )
    assert a == b


def test_content_hash_changes_with_content_order_of_list_model_and_version(monkeypatch):
    base = compute_content_hash({"skills": ["a", "b"]}, USER_IDENTITY_SCHEMA)
    assert base != compute_content_hash({"skills": ["b", "a"]}, USER_IDENTITY_SCHEMA)
    assert base != compute_content_hash({"skills": ["a", "b"], "bio": "x"}, USER_IDENTITY_SCHEMA)
    monkeypatch.setattr(embedding_service, "TEXT_PIPELINE_VERSION", 2)
    assert base != compute_content_hash({"skills": ["a", "b"]}, USER_IDENTITY_SCHEMA)
    monkeypatch.undo()
    monkeypatch.setattr(embedding_service, "EMBEDDING_MODEL", "autre-modele")
    assert base != compute_content_hash({"skills": ["a", "b"]}, USER_IDENTITY_SCHEMA)


def test_content_hash_missing_vs_empty_field_differ_only_if_values_differ():
    assert compute_content_hash({}, USER_IDENTITY_SCHEMA) == compute_content_hash(
        {"bio": None, "skills": None}, USER_IDENTITY_SCHEMA
    )


def test_trending_score_expression_is_built():
    repo = EmbeddingRepository(db=None, tenant_id=uuid.uuid4())
    assert "power" in str(repo._get_trending_score_expr()).lower()
