#!/usr/bin/env python3
"""Embedding generation job for high-throughput 24/7 processing or daily digest.

This script processes decisions that need embeddings. It can run in two modes:
- 'daily': Processes decisions from the last N days (for daily digest).
- 'continuous': Processes as many unembedded decisions as possible within a time limit.

Usage:
    # Daily mode: Process last 1 day of decisions with 10 concurrent requests
    uv run python scripts/embedding_job.py \
        --mode daily \
        --days-back 1 \
        --max-concurrency 10

    # Continuous mode: Process up to 1,000 decisions with 20 concurrent requests
    uv run python scripts/embedding_job.py \
        --mode continuous \
        --max-decisions 1000 \
        --max-concurrency 20 \
        --timeout-minutes 50
"""


# Safely reconfigure standard output and standard error encoding error handling on Windows
import sys
for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass

import argparse
import asyncio
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog

from causaganha.analysis.embedding_models import JINA_V4_1024
from causaganha.pipeline.embedding_pipeline import BatchStats, EmbeddingPipeline
from causaganha.storage.connection import get_connection
from causaganha.storage.embedding_storage import EmbeddingStorage, _get_table_name


logger = structlog.get_logger()


def get_decisions_to_process(mode: str, limit: int | None = None, days_back: int = 1) -> list[int]:
    """Get decisions that need embeddings.

    Args:
        mode: Run mode ('daily' or 'continuous').
        limit: Optional maximum number of decisions to return (for continuous mode).
        days_back: Number of days to look back (for daily mode).

    Returns:
        List of intimation IDs to process.
    """
    con = get_connection("data/causaganha.duckdb")
    table_name = _get_table_name(JINA_V4_1024)

    # Check if embeddings table exists
    tables = con.list_tables()
    if table_name not in tables:
        logger.info("no_embeddings_table_yet", table=table_name)
        if mode == "daily":
            query = """
                SELECT id
                FROM intimations
                WHERE analyzed = TRUE
                  AND analyzed_at > ?
                ORDER BY analyzed_at DESC
            """
        else:
            query = """
                SELECT id
                FROM intimations
                WHERE analyzed = TRUE
                ORDER BY analyzed_at DESC
            """
    elif mode == "daily":
        query = f"""
                SELECT i.id
                FROM intimations i
                LEFT JOIN {table_name} e ON i.id = e.intimation_id
                WHERE i.analyzed = TRUE
                  AND i.analyzed_at > ?
                  AND e.intimation_id IS NULL
                ORDER BY i.analyzed_at DESC
            """
    else:
        query = f"""
                SELECT i.id
                FROM intimations i
                LEFT JOIN {table_name} e ON i.id = e.intimation_id
                WHERE i.analyzed = TRUE
                  AND e.intimation_id IS NULL
                ORDER BY i.analyzed_at DESC
            """

    if mode == "continuous" and limit and limit > 0:
        query += f" LIMIT {limit}"

    if mode == "daily":
        cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
        result = con.con.execute(query, [cutoff_date])
    else:
        result = con.con.execute(query)

    decision_ids = [row[0] for row in result.fetchall()]

    if mode == "daily":
        logger.info(
            "found_decisions_to_process",
            mode=mode,
            count=len(decision_ids),
            days_back=days_back,
            cutoff_date=cutoff_date.isoformat(),
        )
    else:
        logger.info(
            "found_decisions_to_process",
            mode=mode,
            count=len(decision_ids),
            limit=limit or "unlimited",
        )

    return decision_ids


def load_decision_text(intimation_id: int) -> str:
    """Load decision text from database.

    Args:
        intimation_id: Intimation ID to load.

    Returns:
        Decision text.
    """
    con = get_connection("data/causaganha.duckdb")

    query = "SELECT texto FROM intimations WHERE id = ?"
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
    """Create a progress callback that logs processing status.

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
            percent=round(stats.processed_decisions / total * 100, 1) if total > 0 else 0,
            cached=stats.cached_decisions,
            failed=stats.failed_decisions,
            cache_hit_rate=round(stats.cache_hit_rate * 100, 1),
            throughput=round(stats.throughput, 2),
            elapsed_seconds=round(elapsed, 1),
            eta_seconds=round(eta_seconds, 1),
        )

    return progress


def save_statistics(stats: BatchStats, args: argparse.Namespace) -> None:
    """Save job statistics to JSON file.

    Args:
        stats: BatchStats from processing.
        args: Command-line arguments.
    """
    stats_dir = Path("data/stats")
    stats_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    stats_file = stats_dir / f"{args.mode}_{timestamp}.json"

    stats_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "run_type": args.mode,
        "max_concurrency": args.max_concurrency,
        "total_decisions": stats.total_decisions,
        "cached_decisions": stats.cached_decisions,
        "processed_decisions": stats.processed_decisions,
        "failed_decisions": stats.failed_decisions,
        "cache_hit_rate": round(stats.cache_hit_rate, 3),
        "success_rate": round(stats.success_rate, 3),
        "duration_seconds": round(stats.duration_seconds, 2),
        "throughput": round(stats.throughput, 2),
    }

    if args.mode == "daily":
        stats_data["days_back"] = args.days_back
    else:
        stats_data["max_decisions"] = args.max_decisions
        stats_data["timeout_minutes"] = args.timeout_minutes

    with Path(stats_file).open("w") as f:
        json.dump(stats_data, f, indent=2)

    logger.info("statistics_saved", file=str(stats_file))


async def process_batch_with_stats(
    intimation_ids: list[int],
    max_concurrency: int,
    mode: str,
) -> BatchStats:
    """Process decisions.

    Args:
        intimation_ids: List of intimation IDs to process.
        max_concurrency: Maximum concurrent API requests.
        mode: The run mode.

    Returns:
        BatchStats with processing statistics.
    """
    storage = EmbeddingStorage(get_connection("data/causaganha.duckdb"))
    pipeline = EmbeddingPipeline(
        model=JINA_V4_1024,
        max_concurrency=max_concurrency,
        storage=storage,
    )

    start_time = time.time()

    if mode == "continuous":
        progress_callback = create_progress_callback(len(intimation_ids), start_time)
        progress_interval = 10
    else:
        # For daily, we can use the simpler callback if we wanted to,
        # but let's use the detailed one for both or a slightly different one.
        def log_progress(stats) -> None:
            logger.info(
                "progress",
                processed=stats.processed_decisions,
                total=stats.total_decisions,
                cache_hit_rate=f"{stats.cache_hit_rate:.1%}",
                throughput=f"{stats.throughput:.1f} dec/s",
            )

        progress_callback = log_progress
        progress_interval = 100

    logger.info(
        "batch_processing_starting",
        total_decisions=len(intimation_ids),
        max_concurrency=max_concurrency,
        model=JINA_V4_1024.name,
    )

    return await pipeline.process_batch(
        intimation_ids=intimation_ids,
        text_loader=load_decision_text,
        progress_callback=progress_callback,
        progress_interval=progress_interval,
    )


async def main_async(args: argparse.Namespace) -> None:
    """Main async entry point.

    Args:
        args: Command-line arguments.
    """
    job_start = time.time()

    logger.info(
        "embedding_job_starting",
        mode=args.mode,
        max_concurrency=args.max_concurrency,
    )

    # Get unembedded decisions
    limit = args.max_decisions if args.mode == "continuous" and args.max_decisions > 0 else None
    intimation_ids = get_decisions_to_process(
        mode=args.mode,
        limit=limit,
        days_back=args.days_back,
    )

    if not intimation_ids:
        logger.info("no_decisions_to_process")
        empty_stats = BatchStats(
            total_decisions=0,
            cached_decisions=0,
            processed_decisions=0,
            failed_decisions=0,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
        )
        save_statistics(empty_stats, args)
        return

    # Process
    stats = await process_batch_with_stats(
        intimation_ids=intimation_ids,
        max_concurrency=args.max_concurrency,
        mode=args.mode,
    )

    # Save statistics
    save_statistics(stats, args)

    job_duration = time.time() - job_start

    logger.info(
        "embedding_job_complete",
        mode=args.mode,
        total=stats.total_decisions,
        processed=stats.processed_decisions,
        failed=stats.failed_decisions,
        cached=stats.cached_decisions,
        cache_hit_rate=f"{stats.cache_hit_rate:.1%}",
        duration_seconds=round(job_duration, 2),
        throughput=round(stats.throughput, 2),
    )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Embedding generation for processing decisions",
    )

    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["daily", "continuous"],
        help="Run mode: 'daily' (time-filtered) or 'continuous' (unlimited/timeout)",
    )

    parser.add_argument(
        "--days-back",
        type=int,
        default=1,
        help="Number of days to look back (default: 1, daily mode only)",
    )

    parser.add_argument(
        "--max-decisions",
        type=int,
        default=1000,
        help="Maximum decisions to process (0 = unlimited, continuous mode only)",
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
        help="Maximum processing time in minutes (default: 50, continuous mode only)",
    )

    args = parser.parse_args()

    # Run async main
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
