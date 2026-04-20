from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import get_logger
from src.infrastructure.database import get_db

logger = get_logger(__name__)

router = APIRouter(tags=["System & Health"])


@router.get("/livez")
async def liveness_probe():
    """Simple endpoint to check if the API is running."""
    logger.debug("Liveness probe requested")
    return {"status": "alive"}


@router.get("/readyz")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """Endpoint to check if the API is ready to handle requests. It checks database connectivity."""
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


@router.get("/healthz")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Endpoint to check the overall health of the API and its dependencies."""
    logger.debug("Health check requested")
    try:
        await db.execute(text("SELECT 1"))
        db_status = "up"
    except Exception as e:
        logger.warning(f"Health check: Database is down - {str(e)}")
        db_status = "down"

    is_healthy = db_status == "up"

    response = {
        "status": "ok" if is_healthy else "degraded",
        "components": {"api": "up", "database": db_status},
    }

    if not is_healthy:
        logger.error("Health check failed: System is degraded")
        raise HTTPException(status_code=503, detail=response)

    return response
