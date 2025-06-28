import asyncio
import time
from unittest.mock import AsyncMock

from src.download_orchestrator import DownloadOrchestrator


def test_orchestrator_benchmark():
    diarios = [{"id": i} for i in range(20)]
    pipeline = AsyncMock()

    async def _fake(diario):
        await asyncio.sleep(0.001)
        return True

    pipeline.process_diario = AsyncMock(side_effect=_fake)

    orchestrator = DownloadOrchestrator(concurrency=5)
    start = time.perf_counter()
    asyncio.run(orchestrator.run(diarios, pipeline))
    duration = time.perf_counter() - start
    assert duration < 0.1
