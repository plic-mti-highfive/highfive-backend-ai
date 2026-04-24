"""Worker and Queue monitoring utilities for health checks."""

from bullmq import Queue

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


class WorkerMonitor:
    """
    Monitor BullMQ queues health status via Queue API.
    """

    async def get_queue_stats(self, queue_name: str) -> dict:
        """
        Get real-time statistics for a queue (waiting, active, failed, completed).
        """
        queue = Queue(queue_name, {"connection": settings.redis_opts})
        try:
            counts = await queue.getJobCounts("waiting", "active", "failed")
            return counts
        except Exception as e:
            logger.error(f"Error fetching stats for queue '{queue_name}': {str(e)}")
            return {"waiting": 0, "active": 0, "failed": 0}
        finally:
            await queue.close()

    async def get_all_queues_stats(self, queue_names: list[str]) -> dict:
        return {queue: await self.get_queue_stats(queue) for queue in queue_names}

    async def are_workers_healthy(self, queue_names: list[str]) -> bool:
        """
        Basic heuristic: If any queue has >100 waiting jobs and 0 active workers,
        consider it unhealthy.

        This indicates jobs are piling up without being processed.
        """
        stats = await self.get_all_queues_stats(queue_names)

        for q_name, q_stats in stats.items():
            if q_stats.get("waiting", 0) > 100 and q_stats.get("active", 0) == 0:
                return False
        return True
