from fastapi import APIRouter

from src.api.v1 import chat, health, matchmaking

api_router = APIRouter()
api_router.include_router(chat.router)
api_router.include_router(health.router)
api_router.include_router(matchmaking.router)
