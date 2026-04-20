from typing import Awaitable, Callable, Dict

from bullmq import Job
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.interfaces.llm_provider import ILLMProvider
from src.worker.handlers import handle_project_identity, handle_user_identity

JobHandler = Callable[[dict, AsyncSession, ILLMProvider], Awaitable[None]]

JOB_REGISTRY: Dict[str, JobHandler] = {
    "update_user_identity": handle_user_identity,
    "update_project_identity": handle_project_identity,
}


class JobDispatcher:
    """Routes incoming BullMQ jobs to their respective registered handlers."""

    def __init__(self, session_maker: async_sessionmaker, llm_provider: ILLMProvider):
        self.session_maker = session_maker
        self.llm_provider = llm_provider

    async def process(self, job: Job, job_token: str) -> str:
        """Main entrypoint for BullMQ worker instances."""

        handler = JOB_REGISTRY.get(job.name)
        if not handler:
            raise ValueError(f"No handler registered for job: {job.name}")

        async with self.session_maker() as session:
            try:
                await handler(job.data, session, self.llm_provider)
                await session.commit()
                return "Success"
            except Exception as e:
                await session.rollback()
                raise e
