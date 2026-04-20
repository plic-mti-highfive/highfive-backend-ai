import asyncio
import signal

from bullmq import Worker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.infrastructure.llm.openai_provider import OpenAIProvider
from src.worker.dispatcher import JobDispatcher


async def main() -> None:
    """Initialize infrastructure dependencies and start BullMQ queues."""

    engine = create_async_engine(settings.DATABASE_URI, echo=False)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    llm_provider = OpenAIProvider()

    dispatcher = JobDispatcher(session_maker, llm_provider)

    user_worker = Worker(
        "high_priority", dispatcher.process, {"connection": settings.redis_opts, "concurrency": 5}
    )

    project_worker = Worker(
        "default", dispatcher.process, {"connection": settings.redis_opts, "concurrency": 2}
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def shutdown_handler() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)

    await stop_event.wait()

    await user_worker.close()
    await project_worker.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
