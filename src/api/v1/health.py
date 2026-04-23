import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.database import get_db
from src.infrastructure.worker_monitor import WorkerMonitor

logger = get_logger(__name__)

router = APIRouter(tags=["System & Health"])


async def get_required_queues() -> list[str]:
    """
    Get list of required worker queues from configuration.
    """
    workers_config = settings.load_workers_config()
    return [worker.queue for worker in workers_config.workers]


@router.get("/livez")
async def liveness_probe():
    """
    Simple endpoint to check if the API is running.
    """
    logger.debug("Liveness probe requested")
    return {"status": "alive"}


@router.get("/readyz")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """
    Endpoint to check if the API is ready to handle requests. It checks database connectivity.

    Note: Redis and workers are not checked here as the API can still serve cached/legacy data without them.
    """
    logger.debug("Readiness probe requested")
    try:
        await db.execute(text("SELECT 1"))
        logger.debug("Database connection successful")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.warning(f"Readiness probe failed: Database disconnected - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "database": "disconnected", "error": str(e)},
        )


@router.get("/status")
async def status_check(db: AsyncSession = Depends(get_db)):
    """
    Endpoint to check the overall health of the API and its dependencies.

    Includes checks for:
    - Database connectivity (required for operation)
    - Redis connectivity (required for worker queue)
    - Worker availability (required for full operational status)

    Returns:
    - ok: All systems up and running
    - degraded: Core systems up (DB) but auxiliary systems down (Redis/Workers)
    - unavailable: Critical systems down (Database)
    """
    logger.debug("Health check requested")

    db_status = "up"
    redis_status = "up"
    workers_status = "up"

    # 1. DB
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning(f"Health check: Database is down - {str(e)}")
        db_status = "down"

    # 2. Redis
    try:
        r = redis.Redis(**settings.redis_opts)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_status = "down"

    # 3. Workers
    try:
        required_queues = await get_required_queues()
        monitor = WorkerMonitor()
        if not await monitor.are_workers_healthy(required_queues):
            workers_status = "degraded"
    except Exception:
        workers_status = "down"

    # Determine overall health status
    is_healthy = db_status == "up"
    is_fully_operational = db_status == "up" and redis_status == "up" and workers_status == "up"

    response = {
        "status": "ok" if is_fully_operational else ("degraded" if is_healthy else "unavailable"),
        "components": {
            "api": "up",
            "database": db_status,
            "redis": redis_status,
            "workers": workers_status,
        },
    }

    if not is_healthy:
        logger.error("Health check failed: Database is down")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response)

    if not is_fully_operational:
        logger.warning(f"Health check: System is degraded - {response}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response)

    return response


@router.get("/workers-status")
async def workers_status():
    """
    Detailed queue metrics.
    """
    try:
        required_queues = await get_required_queues()
        monitor = WorkerMonitor()
        stats = await monitor.get_all_queues_stats(required_queues)

        return {"status": "ok", "queues": stats}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
