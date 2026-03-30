import uuid
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URI,
    echo=settings.ENV == "dev",
    future=True,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Set the tenant_id in the PostgreSQL session context for RLS."""
    await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))


@asynccontextmanager
async def get_db_with_tenant(tenant_id: uuid.UUID) -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant, false)"),
                {"tenant": str(tenant_id)},
            )
            yield session
        finally:
            await session.execute(text("SELECT set_config('app.current_tenant_id', '', false)"))
            await session.close()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
