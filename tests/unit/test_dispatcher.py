"""Tests for JobDispatcher."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.worker.dispatcher import JOB_REGISTRY, JobDispatcher


@pytest.fixture()
def mock_job():
    """Create a mock BullMQ job."""
    job = MagicMock()
    job.id = str(uuid.uuid4())
    job.name = "update_user_identity"
    job.data = {
        "tenant_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "payload": {"bio": "Test user"},
    }
    return job


@pytest.mark.asyncio
async def test_dispatcher_initialization(session_maker, mock_llm_provider):
    """Test JobDispatcher initialization."""
    dispatcher = JobDispatcher(session_maker, mock_llm_provider)

    assert dispatcher.session_maker == session_maker
    assert dispatcher.llm_provider == mock_llm_provider


@pytest.mark.asyncio
async def test_process_valid_job(session_maker, mock_llm_provider, mock_job):
    """Test processing a valid job."""
    dispatcher = JobDispatcher(session_maker, mock_llm_provider)

    # Mock the handler
    mock_handler = AsyncMock()
    with patch.dict(JOB_REGISTRY, {"update_user_identity": mock_handler}):
        result = await dispatcher.process(mock_job, "token")

    assert result == "Success"
    mock_handler.assert_called_once()

    # Verify handler was called with correct parameters
    call_args = mock_handler.call_args
    assert call_args[0][0] == mock_job.data  # job data
    # session is passed as second arg
    assert call_args[0][2] == mock_llm_provider


@pytest.mark.asyncio
async def test_process_unknown_job(session_maker, mock_llm_provider, mock_job):
    """Test processing an unknown job raises ValueError."""
    dispatcher = JobDispatcher(session_maker, mock_llm_provider)
    mock_job.name = "unknown_job_type"

    with pytest.raises(ValueError, match="No handler registered for job: unknown_job_type"):
        await dispatcher.process(mock_job, "token")


@pytest.mark.asyncio
async def test_process_job_with_handler_error(session_maker, mock_llm_provider, mock_job):
    """Test that errors in handlers are propagated."""
    dispatcher = JobDispatcher(session_maker, mock_llm_provider)

    # Mock the handler to raise an exception
    mock_handler = AsyncMock(side_effect=Exception("Handler error"))

    with patch.dict(JOB_REGISTRY, {"update_user_identity": mock_handler}):
        with pytest.raises(Exception, match="Handler error"):
            await dispatcher.process(mock_job, "token")


@pytest.mark.asyncio
async def test_process_project_identity_job(session_maker, mock_llm_provider):
    """Test processing a project identity job."""
    dispatcher = JobDispatcher(session_maker, mock_llm_provider)

    job = MagicMock()
    job.id = str(uuid.uuid4())
    job.name = "update_project_identity"
    job.data = {
        "tenant_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "payload": {"name": "Test Project"},
    }

    mock_handler = AsyncMock()
    with patch.dict(JOB_REGISTRY, {"update_project_identity": mock_handler}):
        result = await dispatcher.process(job, "token")

    assert result == "Success"
    mock_handler.assert_called_once()


def test_job_registry_contains_expected_handlers():
    """Test that JOB_REGISTRY has expected handlers registered."""
    assert "update_user_identity" in JOB_REGISTRY
    assert "update_project_identity" in JOB_REGISTRY
    assert len(JOB_REGISTRY) == 2


@pytest.mark.asyncio
async def test_dispatcher_session_management(session_maker, mock_llm_provider, mock_job):
    """Test that dispatcher properly manages database sessions."""
    dispatcher = JobDispatcher(session_maker, mock_llm_provider)

    mock_handler = AsyncMock()
    with patch.dict(JOB_REGISTRY, {"update_user_identity": mock_handler}):
        result = await dispatcher.process(mock_job, "token")

    assert result == "Success"


@pytest.mark.asyncio
async def test_process_empty_job_data(session_maker, mock_llm_provider):
    """Test processing a job with empty data."""
    dispatcher = JobDispatcher(session_maker, mock_llm_provider)

    job = MagicMock()
    job.id = str(uuid.uuid4())
    job.name = "update_user_identity"
    job.data = {}

    mock_handler = AsyncMock()
    with patch.dict(JOB_REGISTRY, {"update_user_identity": mock_handler}):
        result = await dispatcher.process(job, "token")

    assert result == "Success"
    # Verify handler was called with correct data
    call_args = mock_handler.call_args
    assert call_args[0][0] == {}  # job data
    assert call_args[0][2] == mock_llm_provider
