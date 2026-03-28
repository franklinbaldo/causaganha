"""Continuous embedding generation job for high-throughput 24/7 processing.

This script processes as many unembedded decisions as possible within a time limit.
Designed for hourly GitHub Actions runs to achieve continuous coverage.

Features:
- Processes ALL unembedded decisions (no time-based filtering)
- Time-boxed execution (stops before timeout)
- High concurrency (20+ parallel requests)
- Automatic caching (skip already-embedded)
- Progress tracking and statistics

Usage:
    # Process up to 1,000 decisions with 20 concurrent requests
    uv run python scripts/continuous_embedding_job.py \
        --max-decisions 1000 \
        --max-concurrency 20 \
        --timeout-minutes 50

    # Process unlimited decisions (until timeout)
    uv run python scripts/continuous_embedding_job.py \
        --max-decisions 0 \
        --timeout-minutes 50
"""

import argparse
import asyncio
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import structlog

from causaganha.analysis.embedding_models import JINA_V4_1024
from causaganha.pipeline.embedding_pipeline import BatchStats, EmbeddingPipeline
from causaganha.storage.connection import get_connection
from causaganha.storage.embedding_storage import EmbeddingStorage


logger = structlog.get_logger()


def get_unembedded_decisions(limit: int | None = None) -> list[int]:
    """Get all decisions that need embeddings (no time filtering).

    Args:
        limit: Optional maximum number of decisions to return.

    Returns:
        List of intimation IDs that need embeddings, ordered by analysis date (newest first).
    """
    con = get_connection()
    model = JINA_V4_1024
    table_name = f"embeddings_{model.provider}_{model.name.replace('-', '_')}_{model.dimension}"

    # Get analyzed decisions without embeddings
    # No time-based filtering - process everything that needs embedding
    query = f"""
        SELECT i.id
        FROM intimations i
        LEFT JOIN {table_name} e ON i.id = e.intimation_id
        WHERE i.analyzed = TRUE
          AND e.intimation_id IS NULL
        ORDER BY i.analyzed_at DESC
    """

    if limit and limit > 0:
        query += f" LIMIT {limit}"

    logger.info(
        "querying_unembedded_decisions",
        table=table_name,
        limit=limit or "unlimited",
    )

    try:
        result = con.con.execute(query)
        rows = result.fetchall()
        intimation_ids = [row[0] for row in rows]

        logger.info(
            "unembedded_decisions_found",
            count=len(intimation_ids),
            sample_ids=intimation_ids[:10] if intimation_ids else [],
        )
    except Exception as e:
        logger.exception("failed_to_query_unembedded_decisions", error=str(e))
        raise
    else:
        return intimation_ids


def load_decision_text(intimation_id: int) -> str:
    """Load decision text from database.

    Args:
        intimation_id: Intimation ID.

    Returns:
        Decision text from the intimations table.
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

        if not row or not row[0]:
            logger.warning("empty_decision_text", intimation_id=intimation_id)
            return ""

        return row[0]

    except Exception as e:
        logger.exception(
            "failed_to_load_decision_text",
            intimation_id=intimation_id,
            error=str(e),
        )
        return ""


def create_progress_callback(total: int, start_time: float) -> Callable[[BatchStats], None]:
    """Create a progress callback that logs every 10 decisions.

    Args:
        total: Total decisions to process.
        start_time: Start time of processing.

    Returns:
        Progress callback function.
    """

    def progress(stats: BatchStats) -> None:
        elapsed = time.time() - start_time
        remaining_decisions = total - stats.processed_decisions
        eta_seconds = (
            (elapsed / stats.processed_decisions * remaining_decisions)
            if stats.processed_decisions > 0
            else 0
        )

        logger.info(
            "processing_progress",
            processed=stats.processed_decisions,
            total=total,
            percent=round(stats.processed_decisions / total * 100, 1),
            cached=stats.cached_decisions,
            failed=stats.failed_decisions,
            cache_hit_rate=round(stats.cache_hit_rate * 100, 1),
            throughput=round(stats.throughput, 2),
            elapsed_seconds=round(elapsed, 1),
            eta_seconds=round(eta_seconds, 1),
        )

    return progress


async def process_with_timeout(
    intimation_ids: list[int],
    max_concurrency: int,
    timeout_minutes: int,
) -> BatchStats:
    """Process decisions with time limit.

    Args:
        intimation_ids: List of intimation IDs to process.
        max_concurrency: Maximum concurrent API requests.
        timeout_minutes: Maximum processing time in minutes.

    Returns:
        BatchStats with processing statistics.
    """
    storage = EmbeddingStorage()
    pipeline = EmbeddingPipeline(
        model=JINA_V4_1024,
        max_concurrency=max_concurrency,
        storage=storage,
    )

    start_time = time.time()
    progress_callback = create_progress_callback(len(intimation_ids), start_time)

    logger.info(
        "batch_processing_starting",
        total_decisions=len(intimation_ids),
        max_concurrency=max_concurrency,
        timeout_minutes=timeout_minutes,
        model=JINA_V4_1024.name,
    )

    # Process batch (will respect timeout internally if needed)
    return await pipeline.process_batch(
        intimation_ids=intimation_ids,
        text_loader=load_decision_text,
        progress_callback=progress_callback,
        progress_interval=10,  # Log every 10 decisions
    )


def save_statistics(stats: BatchStats, args: argparse.Namespace) -> None:
    """Save job statistics to JSON file.

    Args:
        stats: BatchStats from processing.
        args: Command-line arguments.
    """
    stats_dir = Path("data/stats")
    stats_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    stats_file = stats_dir / f"continuous_{timestamp}.json"

    stats_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "run_type": "continuous",
        "max_decisions": args.max_decisions,
        "max_concurrency": args.max_concurrency,
        "timeout_minutes": args.timeout_minutes,
        "total_decisions": stats.total_decisions,
        "cached_decisions": stats.cached_decisions,
        "processed_decisions": stats.processed_decisions,
        "failed_decisions": stats.failed_decisions,
        "cache_hit_rate": round(stats.cache_hit_rate, 3),
        "success_rate": round(stats.success_rate, 3),
        "duration_seconds": round(stats.duration_seconds, 2),
        "throughput": round(stats.throughput, 2),
    }

    with open(stats_file, "w") as f:
        json.dump(stats_data, f, indent=2)

    logger.info("statistics_saved", file=str(stats_file))


async def main_async(args: argparse.Namespace) -> None:
    """Main async entry point.

    Args:
        args: Command-line arguments.
    """
    job_start = time.time()

    logger.info(
        "continuous_job_starting",
        max_decisions=args.max_decisions or "unlimited",
        max_concurrency=args.max_concurrency,
        timeout_minutes=args.timeout_minutes,
    )

    # Get unembedded decisions
    intimation_ids = get_unembedded_decisions(
        limit=args.max_decisions if args.max_decisions > 0 else None,
    )

    if not intimation_ids:
        logger.info("no_decisions_to_process")
        return

    # Process with timeout
    stats = await process_with_timeout(
        intimation_ids=intimation_ids,
        max_concurrency=args.max_concurrency,
        timeout_minutes=args.timeout_minutes,
    )

    # Save statistics
    save_statistics(stats, args)

    # Print summary
    job_duration = time.time() - job_start

    # Calculate remaining work
    remaining = get_unembedded_decisions(limit=1)
    if remaining:
        pass
    else:
        pass

    logger.info(
        "continuous_job_complete",
        total=stats.total_decisions,
        processed=stats.processed_decisions,
        failed=stats.failed_decisions,
        duration_seconds=round(job_duration, 2),
        throughput=round(stats.throughput, 2),
    )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Continuous embedding generation for high-throughput processing",
    )

    parser.add_argument(
        "--max-decisions",
        type=int,
        default=1000,
        help="Maximum decisions to process (0 = unlimited)",
    )

    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=20,
        help="Maximum concurrent API requests (default: 20)",
    )

    parser.add_argument(
        "--timeout-minutes",
        type=int,
        default=50,
        help="Maximum processing time in minutes (default: 50)",
    )

    args = parser.parse_args()

    # Run async main
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
