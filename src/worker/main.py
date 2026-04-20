import asyncio
import signal

from bullmq import Worker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.llm.openai_provider import OpenAIProvider
from src.worker.dispatcher import JobDispatcher

logger = get_logger(__name__)


async def main() -> None:
    """Initialize infrastructure dependencies and start BullMQ queues."""
    logger.info("Initializing worker infrastructure...")

    engine = create_async_engine(settings.DATABASE_URI, echo=False)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    llm_provider = OpenAIProvider()

    dispatcher = JobDispatcher(session_maker, llm_provider)
    logger.info("JobDispatcher initialized")

    user_worker = Worker(
        "high_priority", dispatcher.process, {"connection": settings.redis_opts, "concurrency": 5}
    )
    logger.info("High-priority worker started")

    project_worker = Worker(
        "default", dispatcher.process, {"connection": settings.redis_opts, "concurrency": 2}
    )
    logger.info("Default priority worker started")

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
    await user_worker.close()
    await project_worker.close()
    await engine.dispose()
    logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
