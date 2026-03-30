from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db

router = APIRouter(tags=["System & Health"])


@router.get("/livez")
async def liveness_probe():
    """Simple endpoint to check if the API is running."""
    return {"status": "alive"}


@router.get("/readyz")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """Endpoint to check if the API is ready to handle requests. It checks database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "database": "disconnected", "error": str(e)},
        )


@router.get("/healthz")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Endpoint to check the overall health of the API and its dependencies."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "up"
    except Exception:
        db_status = "down"

    is_healthy = db_status == "up"

    response = {
        "status": "ok" if is_healthy else "degraded",
        "components": {"api": "up", "database": db_status},
    }

    if not is_healthy:
        raise HTTPException(status_code=503, detail=response)

    return response
