import asyncio
from typing import Awaitable, Callable, Dict

from bullmq import Job
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.logger import get_logger, set_worker_id
from src.infrastructure.llm_provider import ILLMProvider
from src.worker.handlers import (
    handle_project_identity,
    handle_project_stats_updated,
    handle_user_identity,
    handle_user_interaction,
)

logger = get_logger(__name__)

JobHandler = Callable[[dict, AsyncSession, ILLMProvider], Awaitable[None]]

JOB_REGISTRY: Dict[str, JobHandler] = {
    "update_user_identity": handle_user_identity,
    "update_project_identity": handle_project_identity,
    "user_interacted_with_project": handle_user_interaction,
    "project_stats_updated": handle_project_stats_updated,
}


class JobDispatcher:
    """
    Routes incoming BullMQ jobs to their respective registered handlers.
    """

    def __init__(
        self,
        session_maker: async_sessionmaker,
        llm_provider: ILLMProvider,
        worker_id: str,
        max_retries: int = 0,
        retry_backoff_ms: int = 1000,
    ):
        self.session_maker = session_maker
        self.llm_provider = llm_provider
        self.worker_id = worker_id
        # Le core publie ses jobs sans option `attempts` (1 seule tentative BullMQ) : les
        # retries de workers.yaml sont donc appliqués ici, en mémoire, avec backoff exponentiel.
        self.max_retries = max_retries
        self.retry_backoff_ms = retry_backoff_ms

    async def process(self, job: Job, job_token: str) -> str:
        """
        Main entrypoint for BullMQ worker instances.
        """
        set_worker_id(self.worker_id)

        logger.info(f"Processing {job.name} (ID: {job.id})")

        handler = JOB_REGISTRY.get(job.name)
        if not handler:
            logger.error(f"No handler registered for job: {job.name}")
            raise ValueError(f"No handler registered for job: {job.name}")

        for attempt in range(self.max_retries + 1):
            async with self.session_maker() as session:
                try:
                    await handler(job.data, session, self.llm_provider)
                    await session.commit()
                    logger.info(f"Job {job.name} (ID: {job.id}) completed successfully")
                    return "Success"
                except Exception as e:
                    await session.rollback()
                    if attempt >= self.max_retries:
                        logger.error(f"Job {job.name} (ID: {job.id}) failed: {str(e)}")
                        raise e
                    delay = self.retry_backoff_ms * (2**attempt) / 1000
                    logger.warning(
                        f"Job {job.name} (ID: {job.id}) failed ({e}), "
                        f"retry {attempt + 1}/{self.max_retries} in {delay:.1f}s"
                    )
            await asyncio.sleep(delay)
