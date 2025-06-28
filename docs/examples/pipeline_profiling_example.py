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
    duration = time.perf_counter() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"Duration: {duration:.2f}s")
    print(f"Peak memory: {peak / 1_048_576:.2f} MB")


if __name__ == "__main__":
    profile_pipeline()
