"""Integration tests for worker functionality."""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import set_tenant_context
from src.models.embedding import Embedding, EntityType, VectorPurpose
from src.worker.handlers import handle_project_identity, handle_user_identity


@pytest.mark.asyncio
async def test_handle_user_identity_integration(
    db_session: AsyncSession, test_tenant_id, mock_llm_provider
):
    """Test user identity handler creates embedding in database."""
    user_id = uuid.uuid4()

    await set_tenant_context(db_session, test_tenant_id)
    await db_session.execute(text("SET ROLE api_tester"))

    data = {
        "tenant_id": str(test_tenant_id),
        "user_id": str(user_id),
        "payload": {
            "bio": "Développeur passionné",
            "skills": ["Python", "FastAPI", "Docker"],
        },
    }

    await handle_user_identity(data, db_session, mock_llm_provider)
    await db_session.flush()

    stmt = select(Embedding).where(
        Embedding.entity_id == user_id,
        Embedding.entity_type == EntityType.USER,
        Embedding.vector_purpose == VectorPurpose.IDENTITY,
        Embedding.tenant_id == test_tenant_id,
    )
    result = await db_session.execute(stmt)
    saved_embedding = result.scalar_one_or_none()

    assert saved_embedding is not None
    assert saved_embedding.entity_type == EntityType.USER
    assert saved_embedding.tenant_id == test_tenant_id
    assert (saved_embedding.vector_data == 0.5).all()


@pytest.mark.asyncio
async def test_handle_project_identity_integration(
    db_session: AsyncSession, test_tenant_id, mock_llm_provider
):
    """Test project identity handler creates embedding in database."""
    project_id = uuid.uuid4()

    await set_tenant_context(db_session, test_tenant_id)
    await db_session.execute(text("SET ROLE api_tester"))

    data = {
        "tenant_id": str(test_tenant_id),
        "project_id": str(project_id),
        "payload": {
            "name": "Mon projet awesome",
            "description": "Une description super cool",
            "tags": ["Python", "FastAPI"],
            "visibility": "PRIVATE",
        },
    }

    await handle_project_identity(data, db_session, mock_llm_provider)
    await db_session.flush()

    stmt = select(Embedding).where(
        Embedding.entity_id == project_id,
        Embedding.entity_type == EntityType.PROJECT,
        Embedding.vector_purpose == VectorPurpose.IDENTITY,
        Embedding.tenant_id == test_tenant_id,
    )
    result = await db_session.execute(stmt)
    saved_embedding = result.scalar_one_or_none()

    assert saved_embedding is not None
    assert saved_embedding.entity_type == EntityType.PROJECT
    assert saved_embedding.tenant_id == test_tenant_id
    assert (saved_embedding.vector_data == 0.5).all()


@pytest.mark.asyncio
async def test_handle_user_identity_with_empty_payload(
    db_session: AsyncSession, test_tenant_id, mock_llm_provider
):
    """Test user identity handler with empty payload."""
    user_id = uuid.uuid4()

    await set_tenant_context(db_session, test_tenant_id)
    await db_session.execute(text("SET ROLE api_tester"))

    data = {
        "tenant_id": str(test_tenant_id),
        "user_id": str(user_id),
    }

    await handle_user_identity(data, db_session, mock_llm_provider)
    await db_session.flush()

    stmt = select(Embedding).where(
        Embedding.entity_id == user_id,
        Embedding.entity_type == EntityType.USER,
        Embedding.tenant_id == test_tenant_id,
    )
    result = await db_session.execute(stmt)
    saved_embedding = result.scalar_one_or_none()

    assert saved_embedding is not None


@pytest.mark.asyncio
async def test_handle_project_identity_with_empty_payload(
    db_session: AsyncSession, test_tenant_id, mock_llm_provider
):
    """Test project identity handler with empty payload."""
    project_id = uuid.uuid4()

    await set_tenant_context(db_session, test_tenant_id)
    await db_session.execute(text("SET ROLE api_tester"))

    data = {
        "tenant_id": str(test_tenant_id),
        "project_id": str(project_id),
    }

    await handle_project_identity(data, db_session, mock_llm_provider)
    await db_session.flush()

    stmt = select(Embedding).where(
        Embedding.entity_id == project_id,
        Embedding.entity_type == EntityType.PROJECT,
        Embedding.tenant_id == test_tenant_id,
    )
    result = await db_session.execute(stmt)
    saved_embedding = result.scalar_one_or_none()

    assert saved_embedding is not None


@pytest.mark.asyncio
async def test_multiple_user_identities_same_tenant(
    db_session: AsyncSession, test_tenant_id, mock_llm_provider
):
    """Test that handlers can process multiple users for same tenant."""
    user_id_1 = uuid.uuid4()
    user_id_2 = uuid.uuid4()

    await set_tenant_context(db_session, test_tenant_id)
    await db_session.execute(text("SET ROLE api_tester"))

    # Create for user 1
    data_1 = {
        "tenant_id": str(test_tenant_id),
        "user_id": str(user_id_1),
        "payload": {"bio": "User 1"},
    }
    await handle_user_identity(data_1, db_session, mock_llm_provider)
    await db_session.flush()

    # Create for user 2
    data_2 = {
        "tenant_id": str(test_tenant_id),
        "user_id": str(user_id_2),
        "payload": {"bio": "User 2"},
    }
    await handle_user_identity(data_2, db_session, mock_llm_provider)
    await db_session.flush()

    # Verify both embeddings exist
    stmt_1 = select(Embedding).where(
        Embedding.entity_id == user_id_1,
        Embedding.tenant_id == test_tenant_id,
    )
    stmt_2 = select(Embedding).where(
        Embedding.entity_id == user_id_2,
        Embedding.tenant_id == test_tenant_id,
    )

    result_1 = await db_session.execute(stmt_1)
    result_2 = await db_session.execute(stmt_2)

    assert result_1.scalar_one_or_none() is not None
    assert result_2.scalar_one_or_none() is not None
