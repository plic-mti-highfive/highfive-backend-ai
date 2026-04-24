import asyncio
import signal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.logger import get_logger
from src.core.nlp_processor import NLPManager
from src.infrastructure.llm.openai_provider import OpenAIProvider
from src.worker.factory import WorkerFactory

logger = get_logger(__name__)


async def main() -> None:
    """
    Initialize infrastructure dependencies and start BullMQ workers.
    """
    logger.info("Initializing worker infrastructure...")

    NLPManager.load_resources()
    engine = create_async_engine(settings.DATABASE_URI, echo=False)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    llm_provider = OpenAIProvider()

    # Load workers configuration and create worker instances
    workers_config = settings.load_workers_config()
    logger.info(f"Loaded config for {len(workers_config.workers)} workers")

    factory = WorkerFactory(session_maker, llm_provider, settings.redis_opts)
    workers = factory.create_workers(workers_config)
    worker_names = factory.get_worker_names(workers)
    logger.info(f"Started workers: {', '.join(worker_names)}")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def shutdown_handler() -> None:
        logger.info("Shutdown signal received, stopping workers...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)

    logger.info("Workers running, waiting for shutdown signal...")
    await stop_event.wait()

    logger.info("Closing workers and database connections...")
    for worker in workers:
        await worker.close()
    await engine.dispose()
    logger.info("Worker shutdown complete")
