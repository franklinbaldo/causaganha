"""Continuous embedding service for running on laptop/personal computer.

This service runs 24/7 on your laptop and continuously processes unembedded decisions.
Designed to be simple, reliable, and resource-efficient.

Features:
- Auto-restart on errors
- Idle sleep when no work
- Progress logging
- Low resource usage
- Simple setup

Usage:
    # Run directly
    uv run python scripts/laptop_service.py

    # Or install as systemd service (Linux)
    sudo cp scripts/causaganha-embeddings.service /etc/systemd/system/
    sudo systemctl enable causaganha-embeddings
    sudo systemctl start causaganha-embeddings

    # Check logs
    journalctl -u causaganha-embeddings -f
"""

import asyncio
import os
import signal
import sys
import time
from datetime import datetime

import structlog

from causaganha.v2.analysis.embedding_models import JINA_V4_1024
from causaganha.v2.pipeline.embedding_pipeline import EmbeddingPipeline
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.embedding_storage import EmbeddingStorage


logger = structlog.get_logger()


class GracefulShutdown:
    """Handle graceful shutdown on SIGTERM/SIGINT."""

    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.info("shutdown_signal_received", signal=signum)
        self.shutdown_requested = True

    def should_stop(self) -> bool:
        return self.shutdown_requested


def get_unembedded_decisions(limit: int = 100) -> list[int]:
    """Get decisions that need embeddings.

    Args:
        limit: Maximum number to return.

    Returns:
        List of intimation IDs.
    """
    con = get_connection()
    model = JINA_V4_1024
    table_name = f"embeddings_{model.provider}_{model.name.replace('-', '_')}_{model.dimension}"

    query = f"""
        SELECT i.id
        FROM intimations i
        LEFT JOIN {table_name} e ON i.id = e.intimation_id
        WHERE i.analyzed = TRUE
          AND e.intimation_id IS NULL
        ORDER BY i.analyzed_at DESC
        LIMIT ?
    """

    try:
        result = con.con.execute(query, [limit])
        rows = result.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        logger.error("query_failed", error=str(e))
        return []


def load_decision_text(intimation_id: int) -> str:
    """Load decision text from database.

    Args:
        intimation_id: Intimation ID.

    Returns:
        Decision text.
    """
    con = get_connection()

    query = """
        SELECT texto
        FROM intimations
        WHERE id = ?
    """

    try:
        result = con.con.execute(query, [intimation_id])
        row = result.fetchone()
        return row[0] if row and row[0] else ""
    except Exception as e:
        logger.error("load_text_failed", intimation_id=intimation_id, error=str(e))
        return ""


async def process_batch(
    pipeline: EmbeddingPipeline,
    intimation_ids: list[int],
) -> dict:
    """Process a batch of decisions.

    Args:
        pipeline: EmbeddingPipeline instance.
        intimation_ids: List of intimation IDs.

    Returns:
        Statistics dictionary.
    """
    try:
        stats = await pipeline.process_batch(
            intimation_ids=intimation_ids,
            text_loader=load_decision_text,
        )

        return {
            "success": True,
            "total": stats.total_decisions,
            "processed": stats.processed_decisions,
            "cached": stats.cached_decisions,
            "failed": stats.failed_decisions,
            "duration": stats.duration_seconds,
            "throughput": stats.throughput,
        }

    except Exception as e:
        logger.error("batch_failed", error=str(e), error_type=type(e).__name__)
        return {
            "success": False,
            "error": str(e),
        }


async def continuous_loop(
    batch_size: int = 50,
    max_concurrency: int = 10,
    idle_sleep: int = 300,
    shutdown: GracefulShutdown = None,
):
    """Main continuous processing loop.

    Args:
        batch_size: Decisions to process per batch.
        max_concurrency: Max concurrent API requests.
        idle_sleep: Seconds to sleep when no work.
        shutdown: GracefulShutdown handler.
    """
    logger.info(
        "service_starting",
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        idle_sleep=idle_sleep,
    )

    # Initialize
    storage = EmbeddingStorage()
    pipeline = EmbeddingPipeline(
        model=JINA_V4_1024,
        max_concurrency=max_concurrency,
        storage=storage,
    )

    iteration = 0
    total_processed = 0
    consecutive_errors = 0
    max_consecutive_errors = 5

    while not (shutdown and shutdown.should_stop()):
        iteration += 1
        start_time = time.time()

        try:
            # Get unembedded decisions
            intimation_ids = get_unembedded_decisions(limit=batch_size)

            if not intimation_ids:
                logger.info(
                    "idle_no_work",
                    iteration=iteration,
                    sleep_seconds=idle_sleep,
                )
                await asyncio.sleep(idle_sleep)
                continue

            logger.info(
                "batch_starting",
                iteration=iteration,
                batch_size=len(intimation_ids),
                total_processed=total_processed,
            )

            # Process batch
            result = await process_batch(pipeline, intimation_ids)

            if result["success"]:
                total_processed += result["processed"]
                consecutive_errors = 0  # Reset error counter

                logger.info(
                    "batch_complete",
                    iteration=iteration,
                    processed=result["processed"],
                    cached=result["cached"],
                    failed=result["failed"],
                    duration=round(result["duration"], 1),
                    throughput=round(result["throughput"], 2),
                    total_processed=total_processed,
                )
            else:
                consecutive_errors += 1
                logger.error(
                    "batch_error",
                    iteration=iteration,
                    consecutive_errors=consecutive_errors,
                    error=result.get("error"),
                )

                # If too many consecutive errors, wait longer before retry
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(
                        "too_many_errors",
                        consecutive_errors=consecutive_errors,
                        sleep_seconds=idle_sleep * 2,
                    )
                    await asyncio.sleep(idle_sleep * 2)
                    consecutive_errors = 0  # Reset after long sleep
                else:
                    # Exponential backoff
                    backoff = 2**consecutive_errors
                    await asyncio.sleep(backoff)

        except Exception as e:
            consecutive_errors += 1
            logger.error(
                "iteration_error",
                iteration=iteration,
                error=str(e),
                error_type=type(e).__name__,
            )

            if consecutive_errors >= max_consecutive_errors:
                logger.error("too_many_errors_exiting", consecutive_errors=consecutive_errors)
                break

            # Backoff
            await asyncio.sleep(2**consecutive_errors)

        # Small sleep between iterations
        iteration_duration = time.time() - start_time
        if iteration_duration < 10:  # If iteration was very fast, add small delay
            await asyncio.sleep(5)

    logger.info(
        "service_stopped",
        total_iterations=iteration,
        total_processed=total_processed,
    )


def main():
    """Entry point."""
    # Configuration from environment variables
    batch_size = int(os.getenv("BATCH_SIZE", "50"))
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "10"))
    idle_sleep = int(os.getenv("IDLE_SLEEP_SECONDS", "300"))

    # Verify API key is set
    if not os.getenv("JINA_API_KEY"):
        logger.error("jina_api_key_not_set")
        print("Error: JINA_API_KEY environment variable not set")
        print("Set it with: export JINA_API_KEY='your-key-here'")
        sys.exit(1)

    logger.info(
        "laptop_service_starting",
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        idle_sleep=idle_sleep,
        timestamp=datetime.utcnow().isoformat(),
        python_version=sys.version,
    )

    print("=" * 80)
    print("CausaGanha Embedding Service (Laptop)")
    print("=" * 80)
    print()
    print(f"  Batch size: {batch_size} decisions")
    print(f"  Concurrency: {max_concurrency} parallel requests")
    print(f"  Idle sleep: {idle_sleep} seconds")
    print(f"  Model: {JINA_V4_1024.name} ({JINA_V4_1024.dimension}D)")
    print()
    print("Service running... (Press Ctrl+C to stop)")
    print()

    # Setup graceful shutdown
    shutdown = GracefulShutdown()

    # Run continuous loop
    try:
        asyncio.run(
            continuous_loop(
                batch_size=batch_size,
                max_concurrency=max_concurrency,
                idle_sleep=idle_sleep,
                shutdown=shutdown,
            ),
        )
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
        print("\nShutting down gracefully...")
    except Exception as e:
        logger.error("service_error", error=str(e))
        print(f"\nError: {e}")
        sys.exit(1)

    print("Service stopped.")


if __name__ == "__main__":
    main()
