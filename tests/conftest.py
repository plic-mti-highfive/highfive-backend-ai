import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import settings

engine = create_async_engine(settings.DATABASE_URI, echo=False, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def verify_db_ready():
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'api_tester') THEN 
                    CREATE ROLE api_tester NOLOGIN; 
                END IF; 
            END $$;
        """)
        )
        await conn.execute(text("GRANT ALL ON TABLE embeddings TO api_tester;"))
    yield


@pytest.fixture()
def test_tenant_id():
    """Generate unique tenant_id for each test (isolation)."""
    return uuid.uuid4()


@pytest_asyncio.fixture()
async def db_session(test_tenant_id):
    """
    DB session for unit tests.
    IMPORTANT: Tests should NOT call commit() - use only flush().
    Rollback at end ensures zero data persists.
    """
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()
