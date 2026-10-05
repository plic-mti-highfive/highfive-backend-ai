import asyncio
import hashlib
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

T = TypeVar("T")


def text_key(namespace: str, text: str) -> str:
    return hashlib.sha256(f"{namespace}\x00{text}".encode("utf-8")).hexdigest()


class LRUCache(Generic[T]):
    """Petit cache LRU en mémoire (un worker = un process, pas de partage nécessaire)."""

    def __init__(self, max_size: int):
        self.max_size = max_size
        self._data: OrderedDict[str, T] = OrderedDict()

    def get(self, key: str) -> T | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: T) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)


BatchFn = Callable[[list[str]], Awaitable[list[list[float]]]]


class EmbeddingBatcher:
    """
    Regroupe les demandes d'embedding arrivant à quelques millisecondes d'intervalle (jobs
    concurrents du worker) en un seul appel au provider, avec :
      - cache LRU (texte identique = aucun appel),
      - dédoublonnage des demandes identiques en vol.
    """

    def __init__(
        self,
        batch_fn: BatchFn,
        namespace: str,
        max_batch_size: int = 64,
        window_seconds: float = 0.02,
        cache_size: int = 1024,
    ):
        self._batch_fn = batch_fn
        self._namespace = namespace
        self._max_batch_size = max_batch_size
        self._window = window_seconds
        self._cache: LRUCache[list[float]] = LRUCache(cache_size)
        self._inflight: dict[str, asyncio.Future[list[float]]] = {}
        self._pending: list[tuple[str, str, asyncio.Future[list[float]]]] = []
        self._timer: asyncio.TimerHandle | None = None
        self._tasks: set[asyncio.Task] = set()

    async def embed(self, text: str) -> list[float]:
        key = text_key(self._namespace, text)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        future = self._inflight.get(key)
        if future is None:
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            self._inflight[key] = future
            self._pending.append((key, text, future))
            if len(self._pending) >= self._max_batch_size:
                self._flush()
            elif self._timer is None:
                self._timer = loop.call_later(self._window, self._flush)
        # shield : l'annulation d'un appelant ne doit pas faire échouer les autres en attente
        return await asyncio.shield(future)

    def _flush(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        batch, self._pending = self._pending, []
        if not batch:
            return
        task = asyncio.get_running_loop().create_task(self._run(batch))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, batch: list[tuple[str, str, asyncio.Future[list[float]]]]) -> None:
        try:
            vectors = await self._batch_fn([text for _, text, _ in batch])
            if len(vectors) != len(batch):
                raise RuntimeError(
                    f"Provider returned {len(vectors)} embeddings for {len(batch)} inputs"
                )
        except Exception as e:
            for key, _, future in batch:
                self._inflight.pop(key, None)
                if not future.done():
                    future.set_exception(e)
                    future.exception()  # exception consultée (évite un warning asyncio)
            return
        for (key, _, future), vector in zip(batch, vectors):
            self._cache.put(key, vector)
            self._inflight.pop(key, None)
            if not future.done():
                future.set_result(vector)
