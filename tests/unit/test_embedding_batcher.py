import asyncio
from types import SimpleNamespace

import pytest

from src.infrastructure.llm.embedding_batcher import EmbeddingBatcher, LRUCache, text_key
from src.infrastructure.llm.openai_provider import OpenAIProvider


def test_lru_cache_evicts_oldest():
    cache = LRUCache[int](2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")
    cache.put("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1 and cache.get("c") == 3


@pytest.mark.asyncio
async def test_concurrent_requests_share_one_call_and_dedupe():
    calls: list[list[str]] = []

    async def batch_fn(texts):
        calls.append(list(texts))
        return [[float(len(t))] for t in texts]

    batcher = EmbeddingBatcher(batch_fn, "m", window_seconds=0.01)
    results = await asyncio.gather(*(batcher.embed(t) for t in ["aa", "bbb", "aa", "c"]))

    assert results == [[2.0], [3.0], [2.0], [1.0]]
    assert len(calls) == 1
    assert sorted(calls[0]) == ["aa", "bbb", "c"]  # "aa" dédoublonné


@pytest.mark.asyncio
async def test_cache_hit_makes_no_call():
    calls = 0

    async def batch_fn(texts):
        nonlocal calls
        calls += 1
        return [[1.0] for _ in texts]

    batcher = EmbeddingBatcher(batch_fn, "m", window_seconds=0.001)
    await batcher.embed("x")
    await batcher.embed("x")
    assert calls == 1


@pytest.mark.asyncio
async def test_max_batch_size_flushes_immediately():
    sizes = []

    async def batch_fn(texts):
        sizes.append(len(texts))
        return [[0.0] for _ in texts]

    batcher = EmbeddingBatcher(batch_fn, "m", max_batch_size=3, window_seconds=10)
    await asyncio.wait_for(asyncio.gather(*(batcher.embed(str(i)) for i in range(3))), 1)
    assert sizes == [3]


@pytest.mark.asyncio
async def test_error_propagates_and_is_not_cached():
    attempts = 0

    async def batch_fn(texts):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("boom")
        return [[1.0] for _ in texts]

    batcher = EmbeddingBatcher(batch_fn, "m", window_seconds=0.001)
    with pytest.raises(RuntimeError):
        await batcher.embed("x")
    assert await batcher.embed("x") == [1.0]


@pytest.mark.asyncio
async def test_openai_provider_batches_and_keeps_order():
    inputs = []

    async def create(input, model):  # noqa: A002
        inputs.append(input)
        # réponse volontairement dans le désordre : l'index fait foi
        data = [SimpleNamespace(index=i, embedding=[float(len(t))]) for i, t in enumerate(input)]
        return SimpleNamespace(data=list(reversed(data)))

    provider = OpenAIProvider()
    provider.client = SimpleNamespace(embeddings=SimpleNamespace(create=create))

    vectors = await provider.generate_embeddings(["a", "bb", "ccc"])

    assert vectors == [[1.0], [2.0], [3.0]]
    assert len(inputs) == 1
    with pytest.raises(ValueError):
        await provider.generate_embedding("  ")


async def test_window_flushes_partial_batch_without_reaching_max_size():
    calls = []

    async def fn(texts):
        calls.append(list(texts))
        return [[float(len(t))] for t in texts]

    b = EmbeddingBatcher(fn, namespace="t", max_batch_size=10, window_seconds=0.01)
    out = await asyncio.gather(b.embed("a"), b.embed("bb"))
    assert out == [[1.0], [2.0]]
    assert calls == [["a", "bb"]]


async def test_namespace_isolates_cache_keys():
    async def fn(texts):
        return [[1.0] for _ in texts]

    assert text_key("m1", "x") != text_key("m2", "x")
    assert text_key("m1", "x") == text_key("m1", "x")


async def test_provider_returning_wrong_count_fails_all_waiters():
    async def fn(texts):
        return [[1.0]]

    b = EmbeddingBatcher(fn, namespace="t", window_seconds=0.005)
    results = await asyncio.gather(b.embed("a"), b.embed("b"), return_exceptions=True)
    assert all(isinstance(r, RuntimeError) for r in results)


async def test_cancelled_caller_does_not_fail_other_waiters():
    async def fn(texts):
        await asyncio.sleep(0.02)
        return [[1.0] for _ in texts]

    b = EmbeddingBatcher(fn, namespace="t", window_seconds=0.005)
    t1 = asyncio.create_task(b.embed("same"))
    t2 = asyncio.create_task(b.embed("same"))
    await asyncio.sleep(0.01)
    t1.cancel()
    assert await t2 == [1.0]


def test_lru_get_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")
    c.put("c", 3)
    assert c.get("b") is None and c.get("a") == 1 and len(c) == 2
