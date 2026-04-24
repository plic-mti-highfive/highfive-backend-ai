"""Tests for BullMQ job handlers."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.worker.handlers import handle_project_identity, handle_user_identity


@pytest.fixture()
def mock_session():
    """Create a mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_handle_user_identity_success(mock_session, mock_llm_provider):
    """Test successful user identity handling."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    data = {
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "payload": {
            "bio": "Développeur passionné",
            "skills": ["Python", "FastAPI"],
        },
    }

    with patch("src.worker.handlers.EmbeddingRepository") as mock_repo_class:
        with patch("src.worker.handlers.EmbeddingService") as mock_service_class:
            mock_repo = AsyncMock()
            mock_service = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_service_class.return_value = mock_service

            await handle_user_identity(data, mock_session, mock_llm_provider)

            mock_repo_class.assert_called_once_with(mock_session, tenant_id)
            mock_service_class.assert_called_once_with(mock_llm_provider, mock_repo, tenant_id)
            mock_service.process_user_identity.assert_called_once_with(
                user_id=user_id,
                payload=data.get("payload", {}),
            )


@pytest.mark.asyncio
async def test_handle_user_identity_empty_payload(mock_session, mock_llm_provider):
    """Test handling user identity with empty payload."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    data = {
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
    }

    with patch("src.worker.handlers.EmbeddingRepository") as mock_repo_class:
        with patch("src.worker.handlers.EmbeddingService") as mock_service_class:
            mock_repo = AsyncMock()
            mock_service = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_service_class.return_value = mock_service

            await handle_user_identity(data, mock_session, mock_llm_provider)

            mock_service.process_user_identity.assert_called_once_with(
                user_id=user_id,
                payload={},
            )


@pytest.mark.asyncio
async def test_handle_project_identity_success(mock_session, mock_llm_provider):
    """Test successful project identity handling."""
    tenant_id = uuid.uuid4()
    project_id = uuid.uuid4()

    data = {
        "tenant_id": str(tenant_id),
        "project_id": str(project_id),
        "payload": {
            "name": "Mon projet awesome",
            "description": "Une description super cool",
            "tags": ["Python", "FastAPI"],
            "visibility": "PRIVATE",
        },
    }

    with patch("src.worker.handlers.EmbeddingRepository") as mock_repo_class:
        with patch("src.worker.handlers.EmbeddingService") as mock_service_class:
            mock_repo = AsyncMock()
            mock_service = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_service_class.return_value = mock_service

            await handle_project_identity(data, mock_session, mock_llm_provider)

            mock_repo_class.assert_called_once_with(mock_session, tenant_id)
            mock_service_class.assert_called_once_with(mock_llm_provider, mock_repo, tenant_id)
            mock_service.process_project_identity.assert_called_once_with(
                project_id=project_id,
                payload=data.get("payload", {}),
            )


@pytest.mark.asyncio
async def test_handle_project_identity_empty_payload(mock_session, mock_llm_provider):
    """Test handling project identity with empty payload."""
    tenant_id = uuid.uuid4()
    project_id = uuid.uuid4()

    data = {
        "tenant_id": str(tenant_id),
        "project_id": str(project_id),
    }

    with patch("src.worker.handlers.EmbeddingRepository") as mock_repo_class:
        with patch("src.worker.handlers.EmbeddingService") as mock_service_class:
            mock_repo = AsyncMock()
            mock_service = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_service_class.return_value = mock_service

            await handle_project_identity(data, mock_session, mock_llm_provider)

            mock_service.process_project_identity.assert_called_once_with(
                project_id=project_id,
                payload={},
            )


@pytest.mark.asyncio
async def test_handle_user_identity_with_string_uuids(mock_session, mock_llm_provider):
    """Test handling user identity properly converts string UUIDs."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    data = {
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "payload": {"bio": "Test"},
    }

    with patch("src.worker.handlers.EmbeddingRepository") as mock_repo_class:
        with patch("src.worker.handlers.EmbeddingService") as mock_service_class:
            mock_repo = AsyncMock()
            mock_service = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_service_class.return_value = mock_service

            await handle_user_identity(data, mock_session, mock_llm_provider)

            # Verify UUIDs were properly converted
            call_args = mock_service.process_user_identity.call_args
            assert call_args[1]["user_id"] == user_id
            assert isinstance(call_args[1]["user_id"], uuid.UUID)


@pytest.mark.asyncio
async def test_handle_project_identity_with_string_uuids(mock_session, mock_llm_provider):
    """Test handling project identity properly converts string UUIDs."""
    tenant_id = uuid.uuid4()
    project_id = uuid.uuid4()

    data = {
        "tenant_id": str(tenant_id),
        "project_id": str(project_id),
        "payload": {"name": "Project"},
    }

    with patch("src.worker.handlers.EmbeddingRepository") as mock_repo_class:
        with patch("src.worker.handlers.EmbeddingService") as mock_service_class:
            mock_repo = AsyncMock()
            mock_service = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_service_class.return_value = mock_service

            await handle_project_identity(data, mock_session, mock_llm_provider)

            # Verify UUIDs were properly converted
            call_args = mock_service.process_project_identity.call_args
            assert call_args[1]["project_id"] == project_id
            assert isinstance(call_args[1]["project_id"], uuid.UUID)


@pytest.mark.asyncio
async def test_handle_user_identity_creates_correct_repositories(mock_session, mock_llm_provider):
    """Test that handler creates repositories with correct tenant context."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    data = {
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "payload": {},
    }

    with patch("src.worker.handlers.EmbeddingRepository") as mock_repo_class:
        with patch("src.worker.handlers.EmbeddingService") as mock_service_class:
            mock_repo = AsyncMock()
            mock_service = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_service_class.return_value = mock_service

            await handle_user_identity(data, mock_session, mock_llm_provider)

            # Verify repository is created with correct session and tenant
            mock_repo_class.assert_called_once()
            call_args = mock_repo_class.call_args
            assert call_args[0][0] == mock_session
            assert call_args[0][1] == tenant_id
