"""Example: Profile memory and CPU usage of the async pipeline."""

from __future__ import annotations

import asyncio
import sys
import time
import tracemalloc

from src.async_diario_pipeline import main as pipeline_main


def profile_pipeline(max_items: int = 1) -> None:
    """Run the pipeline with tracemalloc and print stats."""
    sys.argv = [
        "async_diario_pipeline.py",
        "--max-items",
        str(max_items),
        "--stats-only",
    ]
    tracemalloc.start()
    start = time.perf_counter()
    asyncio.run(pipeline_main())
    time.perf_counter() - start
    _current, _peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()


if __name__ == "__main__":
    profile_pipeline()
