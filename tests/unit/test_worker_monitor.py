"""Tests for WorkerMonitor."""

from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.worker_monitor import WorkerMonitor


@pytest.mark.asyncio
async def test_worker_monitor_initialization():
    """Test WorkerMonitor initialization."""
    monitor = WorkerMonitor()
    assert monitor is not None


@pytest.mark.asyncio
async def test_get_queue_stats_success(redis_opts):
    """Test getting queue statistics successfully."""
    monitor = WorkerMonitor()

    with patch("src.infrastructure.worker_monitor.Queue") as mock_queue_class:
        mock_queue = AsyncMock()
        mock_queue_class.return_value = mock_queue

        mock_queue.getJobCounts.return_value = {
            "waiting": 5,
            "active": 2,
            "failed": 1,
        }

        stats = await monitor.get_queue_stats("test_queue")

        assert stats["waiting"] == 5
        assert stats["active"] == 2
        assert stats["failed"] == 1
        mock_queue.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_queue_stats_error_handling(redis_opts):
    """Test queue stats error handling."""
    monitor = WorkerMonitor()

    with patch("src.infrastructure.worker_monitor.Queue") as mock_queue_class:
        mock_queue = AsyncMock()
        mock_queue_class.return_value = mock_queue

        mock_queue.getJobCounts.side_effect = Exception("Redis connection error")

        stats = await monitor.get_queue_stats("test_queue")

        assert stats == {"waiting": 0, "active": 0, "failed": 0}
        mock_queue.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_queue_stats_closes_queue_on_error(redis_opts):
    """Test that queue is closed even on error."""
    monitor = WorkerMonitor()

    with patch("src.infrastructure.worker_monitor.Queue") as mock_queue_class:
        mock_queue = AsyncMock()
        mock_queue_class.return_value = mock_queue
        mock_queue.getJobCounts.side_effect = Exception("Error")

        await monitor.get_queue_stats("test_queue")

        mock_queue.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_queues_stats(redis_opts):
    """Test getting statistics for all queues."""
    monitor = WorkerMonitor()

    with patch("src.infrastructure.worker_monitor.Queue") as mock_queue_class:
        mock_queue = AsyncMock()
        mock_queue_class.return_value = mock_queue

        mock_queue.getJobCounts.return_value = {
            "waiting": 3,
            "active": 1,
            "failed": 0,
        }

        queue_names = ["high_priority", "default"]
        all_stats = await monitor.get_all_queues_stats(queue_names)

        assert len(all_stats) == 2
        assert all_stats["high_priority"]["waiting"] == 3
        assert all_stats["default"]["waiting"] == 3


@pytest.mark.asyncio
async def test_get_all_queues_stats_mixed_results(redis_opts):
    """Test getting statistics for multiple queues with different results."""
    monitor = WorkerMonitor()

    async def mock_get_job_counts(*args):
        return {"waiting": 5, "active": 2, "failed": 1}

    with patch("src.infrastructure.worker_monitor.Queue") as mock_queue_class:
        mock_queue = AsyncMock()
        mock_queue_class.return_value = mock_queue
        mock_queue.getJobCounts = mock_get_job_counts

        queue_names = ["queue1", "queue2"]
        all_stats = await monitor.get_all_queues_stats(queue_names)

        assert len(all_stats) == 2
        for queue_name in queue_names:
            assert all_stats[queue_name]["waiting"] == 5


@pytest.mark.asyncio
async def test_are_workers_healthy_with_healthy_queues(redis_opts):
    """Test worker health check with healthy queues."""
    monitor = WorkerMonitor()

    with patch.object(
        monitor, "get_all_queues_stats"
    ) as mock_get_stats:
        mock_get_stats.return_value = {
            "high_priority": {"waiting": 10, "active": 2, "failed": 0},
            "default": {"waiting": 5, "active": 1, "failed": 0},
        }

        health = await monitor.are_workers_healthy(["high_priority", "default"])

        assert health is True


@pytest.mark.asyncio
async def test_are_workers_healthy_with_unhealthy_queue(redis_opts):
    """Test worker health check with unhealthy queues."""
    monitor = WorkerMonitor()

    with patch.object(
        monitor, "get_all_queues_stats"
    ) as mock_get_stats:
        mock_get_stats.return_value = {
            "high_priority": {"waiting": 150, "active": 0, "failed": 0},
            "default": {"waiting": 5, "active": 1, "failed": 0},
        }

        health = await monitor.are_workers_healthy(["high_priority", "default"])

        assert health is False


@pytest.mark.asyncio
async def test_are_workers_healthy_empty_queues(redis_opts):
    """Test worker health check with empty queue stats."""
    monitor = WorkerMonitor()

    with patch.object(
        monitor, "get_all_queues_stats"
    ) as mock_get_stats:
        mock_get_stats.return_value = {
            "queue1": {"waiting": 0, "active": 0, "failed": 0},
        }

        health = await monitor.are_workers_healthy(["queue1"])

        assert health is True


@pytest.mark.asyncio
async def test_are_workers_healthy_high_waiting_low_active(redis_opts):
    """Test health check detects high waiting jobs with low active workers."""
    monitor = WorkerMonitor()

    with patch.object(
        monitor, "get_all_queues_stats"
    ) as mock_get_stats:
        mock_get_stats.return_value = {
            "problem_queue": {"waiting": 200, "active": 0, "failed": 50},
        }

        health = await monitor.are_workers_healthy(["problem_queue"])

        assert health is False


@pytest.mark.asyncio
async def test_are_workers_healthy_exactly_threshold(redis_opts):
    """Test health check with exactly 100 waiting jobs."""
    monitor = WorkerMonitor()

    with patch.object(
        monitor, "get_all_queues_stats"
    ) as mock_get_stats:
        # At exactly 100 waiting with 0 active, should be healthy (>100 is threshold)
        mock_get_stats.return_value = {
            "edge_case": {"waiting": 100, "active": 0, "failed": 0},
        }

        health = await monitor.are_workers_healthy(["edge_case"])

        assert health is True


@pytest.mark.asyncio
async def test_are_workers_healthy_over_threshold_with_active(redis_opts):
    """Test health with >100 waiting but has active workers."""
    monitor = WorkerMonitor()

    with patch.object(
        monitor, "get_all_queues_stats"
    ) as mock_get_stats:
        # Even with >100 waiting, if active > 0, it's healthy
        mock_get_stats.return_value = {
            "processing": {"waiting": 150, "active": 3, "failed": 0},
        }

        health = await monitor.are_workers_healthy(["processing"])

        assert health is True


@pytest.mark.asyncio
async def test_get_queue_stats_empty_queue(redis_opts):
    """Test getting stats for an empty queue."""
    monitor = WorkerMonitor()

    with patch("src.infrastructure.worker_monitor.Queue") as mock_queue_class:
        mock_queue = AsyncMock()
        mock_queue_class.return_value = mock_queue

        mock_queue.getJobCounts.return_value = {
            "waiting": 0,
            "active": 0,
            "failed": 0,
        }

        stats = await monitor.get_queue_stats("empty_queue")

        assert stats["waiting"] == 0
        assert stats["active"] == 0
        assert stats["failed"] == 0
