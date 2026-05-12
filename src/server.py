from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.logger import get_logger
from src.core.middlewares import TimingMiddleware
from src.core.nlp_processor import NLPManager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    NLPManager.load_resources()

    yield
    logger.info("Shutting down FastAPI app, performing cleanup if necessary...")
    # await engine.dispose()


def create_app() -> FastAPI:
    logger.info(f"Creating FastAPI app version {settings.VERSION} in {settings.ENV} environment")
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
