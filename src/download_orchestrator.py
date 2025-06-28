from __future__ import annotations

import asyncio
from typing import List, Dict, Any, Callable


class DownloadOrchestrator:
    """Queue-based orchestrator for download jobs."""

    def __init__(self, concurrency: int = 3) -> None:
        self.concurrency = concurrency

    async def run(
        self, diarios: List[Dict[str, Any]], pipeline: Callable[[Dict[str, Any]], asyncio.Future]
    ) -> List[bool]:
        """Process diarios using a worker queue."""
        queue: asyncio.Queue[Dict[str, Any] | object] = asyncio.Queue()
        for item in diarios:
            await queue.put(item)

        results: List[bool] = []
        sentinel = object()

        async def worker() -> None:
            while True:
                diario = await queue.get()
                if diario is sentinel:
                    queue.task_done()
                    break
                try:
                    result = await pipeline.process_diario(diario)
                    results.append(result)
                finally:
                    queue.task_done()

        tasks = [asyncio.create_task(worker()) for _ in range(self.concurrency)]

        for _ in range(self.concurrency):
            await queue.put(sentinel)

        await queue.join()
        for t in tasks:
            await t
        return results
