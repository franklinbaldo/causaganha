"""Module for the worker pool to run ML tasks in parallel."""

import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Any, List
import structlog

logger = structlog.get_logger()

class WorkerPool:
    """
    A simple worker pool to run CPU-bound tasks in a separate process pool,
    making them non-blocking for the main asyncio event loop.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initializes the worker pool.

        Args:
            max_workers: The maximum number of worker processes.
        """
        self.max_workers = max_workers
        self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        logger.info("worker_pool_initialized", max_workers=self.max_workers)

    async def run_in_parallel(self, tasks: List[Tuple[Callable, List[Any]]]) -> List[Any]:
        """
        Runs a list of tasks in parallel using the process pool.

        Args:
            tasks: A list of tuples, where each tuple contains:
                   - The function to execute.
                   - A list of arguments for the function.

        Returns:
            A list of results from the executed tasks, in the same order.
        """
        loop = asyncio.get_running_loop()
        futures = [loop.run_in_executor(self.executor, func, *args) for func, args in tasks]

        results = await asyncio.gather(*futures)
        return results

    def shutdown(self):
        """Shuts down the worker pool executor."""
        logger.info("shutting_down_worker_pool")
        self.executor.shutdown(wait=True)

# Example usage (for testing or demonstration)
def example_cpu_bound_task(x, y):
    """A simple function that simulates a CPU-bound task."""
    return x * y

async def main():
    """Example of how to use the WorkerPool."""
    pool = WorkerPool(max_workers=2)

    tasks_to_run = [
        (example_cpu_bound_task, [2, 3]),
        (example_cpu_bound_task, [4, 5]),
        (example_cpu_bound_task, [6, 7]),
    ]

    print("Running tasks in parallel...")
    results = await pool.run_in_parallel(tasks_to_run)
    print(f"Results: {results}")

    pool.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
