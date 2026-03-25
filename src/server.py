from fastapi import FastAPI

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.middlewares import TimingMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="HighFive! AI API",
        description="AI microservice for HighFive!",
        version=settings.VERSION,
    )

    app.add_middleware(TimingMiddleware)

    app.include_router(api_router, prefix="/api/v1")

    return app
