import asyncio
from unittest.mock import AsyncMock

from src.download_orchestrator import DownloadOrchestrator


def test_orchestrator_runs_jobs_concurrently():
    diarios = [{"id": i} for i in range(5)]
    pipeline = AsyncMock()

    async def _fake(diario):
        await asyncio.sleep(0.01)
        return True

    pipeline.process_diario = AsyncMock(side_effect=_fake)

    orchestrator = DownloadOrchestrator(concurrency=2)
    results = asyncio.run(orchestrator.run(diarios, pipeline))

    assert len(results) == 5
    assert pipeline.process_diario.call_count == 5
