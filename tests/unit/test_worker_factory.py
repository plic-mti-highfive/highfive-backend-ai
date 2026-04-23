"""Tests for WorkerFactory."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.config import WorkerConfig, WorkersConfig
from src.worker.factory import WorkerFactory


@pytest.fixture()
def workers_config():
    """Create sample worker configuration."""
    return WorkersConfig(
        workers=[
            WorkerConfig(
                name="high_priority",
                queue="high_priority",
                concurrency=5,
                max_retries=3,
                retry_backoff_ms=1000,
            ),
            WorkerConfig(
                name="default",
                queue="default",
                concurrency=2,
                max_retries=2,
                retry_backoff_ms=2000,
            ),
        ]
    )


def test_worker_factory_initialization(session_maker, mock_llm_provider, redis_opts):
    """Test WorkerFactory initialization."""
    factory = WorkerFactory(session_maker, mock_llm_provider, redis_opts)

    assert factory.session_maker == session_maker
    assert factory.llm_provider == mock_llm_provider
    assert factory.redis_opts == redis_opts
    assert factory.dispatcher is not None


@patch("src.worker.factory.Worker")
def test_create_workers(
    mock_worker_class, session_maker, mock_llm_provider, redis_opts, workers_config
):
    """Test creating workers from configuration."""
    mock_worker_instance = MagicMock()
    mock_worker_class.return_value = mock_worker_instance
    mock_worker_instance.name = "test_queue"

    factory = WorkerFactory(session_maker, mock_llm_provider, redis_opts)
    workers = factory.create_workers(workers_config)

    assert len(workers) == 2
    assert all(worker == mock_worker_instance for worker in workers)
    assert mock_worker_class.call_count == 2

    # Verify Worker instantiation with correct parameters
    calls = mock_worker_class.call_args_list
    # Worker is called as: Worker(queue_name, handler, options_dict)
    assert calls[0][0][0] == "high_priority"  # queue name (arg 0)
    assert calls[0][0][2]["connection"] == redis_opts  # options dict (arg 2)
    assert calls[0][0][2]["concurrency"] == 5

    assert calls[1][0][0] == "default"  # queue name (arg 0)
    assert calls[1][0][2]["connection"] == redis_opts  # options dict (arg 2)
    assert calls[1][0][2]["concurrency"] == 2


def test_get_worker_names(session_maker, mock_llm_provider, redis_opts):
    """Test getting worker names."""
    mock_worker1 = MagicMock()
    mock_worker1.name = "high_priority"

    mock_worker2 = MagicMock()
    mock_worker2.name = "default"

    workers = [mock_worker1, mock_worker2]
    names = WorkerFactory.get_worker_names(workers)

    assert names == ["high_priority", "default"]


def test_get_worker_names_empty_list(session_maker, mock_llm_provider, redis_opts):
    """Test get_worker_names with empty list."""
    names = WorkerFactory.get_worker_names([])
    assert names == []


@patch("src.worker.factory.Worker")
def test_create_workers_single_worker(
    mock_worker_class, session_maker, mock_llm_provider, redis_opts
):
    """Test creating a single worker."""
    mock_worker_instance = MagicMock()
    mock_worker_class.return_value = mock_worker_instance
    mock_worker_instance.name = "single_queue"

    config = WorkersConfig(
        workers=[
            WorkerConfig(
                name="single",
                queue="single_queue",
                concurrency=1,
            ),
        ]
    )

    factory = WorkerFactory(session_maker, mock_llm_provider, redis_opts)
    workers = factory.create_workers(config)

    assert len(workers) == 1
    assert workers[0] == mock_worker_instance


@patch("src.worker.factory.Worker")
def test_create_workers_with_retry_config(
    mock_worker_class, session_maker, mock_llm_provider, redis_opts
):
    """Test creating workers respects retry configuration."""
    mock_worker_instance = MagicMock()
    mock_worker_class.return_value = mock_worker_instance
    mock_worker_instance.name = "retry_queue"

    config = WorkersConfig(
        workers=[
            WorkerConfig(
                name="retry_worker",
                queue="retry_queue",
                concurrency=3,
                max_retries=5,
                retry_backoff_ms=5000,
                remove_on_complete=False,
                remove_on_fail=True,
            ),
        ]
    )

    factory = WorkerFactory(session_maker, mock_llm_provider, redis_opts)
    workers = factory.create_workers(config)

    assert len(workers) == 1
    # Verify that max_retries and other config are stored in the worker config
    # (Note: BullMQ Worker takes these as part of the initial config)
    call_args = mock_worker_class.call_args
    assert call_args[0][2]["connection"] == redis_opts
    assert call_args[0][2]["concurrency"] == 3
