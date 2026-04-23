from typing import Awaitable, Callable, Dict

from bullmq import Job
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.logger import get_logger
from src.infrastructure.llm_provider import ILLMProvider
from src.worker.handlers import handle_project_identity, handle_user_identity

logger = get_logger(__name__)

JobHandler = Callable[[dict, AsyncSession, ILLMProvider], Awaitable[None]]

JOB_REGISTRY: Dict[str, JobHandler] = {
    "update_user_identity": handle_user_identity,
    "update_project_identity": handle_project_identity,
}


class JobDispatcher:
    """
    Routes incoming BullMQ jobs to their respective registered handlers.
    """

    def __init__(self, session_maker: async_sessionmaker, llm_provider: ILLMProvider):
        self.session_maker = session_maker
        self.llm_provider = llm_provider

    async def process(self, job: Job, job_token: str) -> str:
        """
        Main entrypoint for BullMQ worker instances.
        """
        logger.info(f"Processing job: {job.name} (ID: {job.id})")

        handler = JOB_REGISTRY.get(job.name)
        if not handler:
            logger.error(f"No handler registered for job: {job.name}")
            raise ValueError(f"No handler registered for job: {job.name}")

        async with self.session_maker() as session:
            try:
                await handler(job.data, session, self.llm_provider)
                await session.commit()
                logger.info(f"Job {job.name} (ID: {job.id}) completed successfully")
                return "Success"
            except Exception as e:
                logger.error(f"Job {job.name} (ID: {job.id}) failed: {str(e)}")
                await session.rollback()
                raise e
