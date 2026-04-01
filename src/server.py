from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.middlewares import TimingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):

    yield
    # await engine.dispose()


def create_app() -> FastAPI:
    print(f"Creating FastAPI app version {settings.VERSION} in {settings.ENV} environment")
    app = FastAPI(
        title="HighFive! AI API",
        description="AI microservice for HighFive!",
        version=settings.VERSION,
        lifespan=lifespan,
        root_path="/ai",
    )

    app.add_middleware(TimingMiddleware)

    app.include_router(api_router, prefix="/api/v1")

    return app
