"""Worker factory to instantiate BullMQ workers from configuration."""

from bullmq import Worker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import WorkersConfig
from src.core.logger import get_logger
from src.infrastructure.llm_provider import ILLMProvider
from src.worker.dispatcher import JobDispatcher

logger = get_logger(__name__)


class WorkerFactory:
    """
    Factory for creating and managing BullMQ workers from configuration.
    """

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        llm_provider: ILLMProvider,
        redis_opts: dict,
    ):
        """
        Initialize the worker factory.

        Parmeters:
            session_maker: SQLAlchemy async session factory
            llm_provider: LLM provider instance
            redis_opts: Redis connection options (host, port)
        """
        self.session_maker = session_maker
        self.llm_provider = llm_provider
        self.redis_opts = redis_opts

    def create_workers(self, workers_config: WorkersConfig) -> list[Worker]:
        """
        Create worker instances from configuration.

        Parmeters:
            workers_config: Configuration containing list of workers to create

        Returns:
            List of instantiated BullMQ Worker objects
        """
        workers = []

        for worker_cfg in workers_config.workers:
            logger.info(
                f"Creating worker '{worker_cfg.name}' for queue '{worker_cfg.queue}' "
                f"concurrency={worker_cfg.concurrency}"
            )

            dispatcher = JobDispatcher(self.session_maker, self.llm_provider, worker_cfg.name)

            worker = Worker(
                worker_cfg.queue,
                dispatcher.process,
                {
                    "connection": self.redis_opts,
                    "concurrency": worker_cfg.concurrency,
                    "name": worker_cfg.name,
                },
            )

            workers.append(worker)

        return workers

    @staticmethod
    def get_worker_names(workers: list[Worker]) -> list[str]:
        """
        Get names of all workers.

        Parmeters:
            workers: List of Worker instances

        Returns:
            List of worker names (queue names)
        """
        return [worker.name for worker in workers]
