import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import settings
from src.core.nlp_processor import NLPManager

engine = create_async_engine(settings.DATABASE_URI, echo=False, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_nlp():
    """Initialize NLPManager resources at test session start."""
    NLPManager.load_resources()
    yield


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


@pytest.fixture()
def mock_llm_provider():
    """Mock LLM provider for testing."""
    mock = AsyncMock()
    mock.generate_embedding.return_value = [0.5] * 1536
    mock.extract_metadata.return_value = {
        "theme": "Informatique",
        "sub_themes": ["Backend", "APIs"],
    }
    return mock


@pytest.fixture()
def redis_opts():
    """Redis connection options for testing."""
    return settings.redis_opts


@pytest.fixture()
def session_maker():
    """Session maker factory for tests."""
    return TestingSessionLocal
