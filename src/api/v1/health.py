from fastapi import APIRouter

from src.core import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    return {
        "status": "ok",
        "environment": settings.ENV,
    }
