"""Worker BullMQ de charge : mêmes workers/config que la prod, mais provider factice.

    uv run python -m load.run_worker --latency 0.05

`--latency` simule le temps de réponse d'OpenAI par appel (embedding ou chat).
"""

import argparse
import asyncio
import signal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from scripts.fake_provider import FakeLLMProvider
from src.core.config import settings
from src.core.nlp_processor import NLPManager
from src.worker.factory import WorkerFactory


async def main(latency: float) -> None:
    NLPManager.load_resources()
    engine = create_async_engine(settings.DATABASE_URI, pool_size=10, max_overflow=5)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    workers = WorkerFactory(maker, FakeLLMProvider(latency), settings.redis_opts).create_workers(
        settings.load_workers_config()
    )
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, stop.set)
    print("worker de charge démarré", flush=True)
    await stop.wait()
    for w in workers:
        await w.close(force=True)
    await engine.dispose()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--latency", type=float, default=0.05)
    asyncio.run(main(ap.parse_args().latency))
