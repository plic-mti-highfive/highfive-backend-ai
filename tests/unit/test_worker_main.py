"""Bootstrap du worker (src/worker/main.py) : tout est simulé, aucun réseau ni Redis."""

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import WorkerConfig, WorkersConfig
from src.worker import main as worker_main


def _patched(workers):
    engine = MagicMock()
    engine.dispose = AsyncMock()
    factory = MagicMock()
    factory.create_workers.return_value = workers
    factory.get_worker_names.return_value = [w.name for w in workers]
    config = WorkersConfig(workers=[WorkerConfig(name="w1", queue="q1")])
    return engine, factory, config


@pytest.mark.asyncio
async def test_main_starts_workers_then_closes_them_on_sigterm():
    w1, w2 = MagicMock(), MagicMock()
    w1.name, w2.name = "w1", "w2"
    w1.close, w2.close = AsyncMock(), AsyncMock()
    engine, factory, config = _patched([w1, w2])
    handlers = {}
    fake_loop = MagicMock()
    fake_loop.add_signal_handler.side_effect = lambda sig, cb: handlers.__setitem__(sig, cb)

    with (
        patch.object(worker_main.NLPManager, "load_resources") as load_nlp,
        patch.object(worker_main, "create_async_engine", return_value=engine),
        patch.object(worker_main, "OpenAIProvider") as provider,
        patch.object(worker_main, "WorkerFactory", return_value=factory) as factory_cls,
        patch.object(worker_main.settings.__class__, "load_workers_config", return_value=config),
        patch.object(worker_main.asyncio, "get_running_loop", return_value=fake_loop),
    ):
        task = asyncio.create_task(worker_main.main())
        for _ in range(50):
            if signal.SIGTERM in handlers:
                break
            await asyncio.sleep(0.01)
        assert set(handlers) == {signal.SIGINT, signal.SIGTERM}
        assert not task.done()  # le worker tourne tant qu'aucun signal n'est reçu
        handlers[signal.SIGTERM]()
        await asyncio.wait_for(task, timeout=2)

    load_nlp.assert_called_once()
    provider.assert_called_once()
    assert factory_cls.call_args.args[1] is provider.return_value
    factory.create_workers.assert_called_once_with(config)
    w1.close.assert_awaited_once()
    w2.close.assert_awaited_once()
    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_fails_fast_when_workers_config_is_missing():
    engine, factory, _ = _patched([])
    with (
        patch.object(worker_main.NLPManager, "load_resources"),
        patch.object(worker_main, "create_async_engine", return_value=engine),
        patch.object(worker_main, "OpenAIProvider"),
        patch.object(
            worker_main.settings.__class__,
            "load_workers_config",
            side_effect=FileNotFoundError("workers.yaml"),
        ),
    ):
        with pytest.raises(FileNotFoundError):
            await worker_main.main()
