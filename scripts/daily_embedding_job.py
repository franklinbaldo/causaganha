#!/usr/bin/env python3
"""Daily embedding generation job for GitHub Actions.

Processes decisions from the last N days that don't have embeddings yet.
Optimized for daily digest processing with caching.
"""

import argparse
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import structlog

from causaganha.analysis.embedding_models import JINA_V4_1024
from causaganha.pipeline.embedding_pipeline import EmbeddingPipeline
from causaganha.storage.connection import get_connection
from causaganha.storage.embedding_storage import EmbeddingStorage


logger = structlog.get_logger()


def get_decisions_to_process(days_back: int = 1) -> list[int]:
    """Get decisions from last N days that need embeddings.

    Args:
        days_back: Number of days to look back.

    Returns:
        List of intimation IDs to process.
    """
    con = get_connection("data/causaganha.duckdb")

    # Get table name for checking existing embeddings
    from causaganha.storage.embedding_storage import _get_table_name

    table_name = _get_table_name(JINA_V4_1024)

    # Check if embeddings table exists
    if table_name not in con.list_tables():
        logger.info("no_embeddings_table_yet", table=table_name)
        # Get all analyzed decisions
        query = """
            SELECT id
            FROM intimations
            WHERE analyzed = TRUE
              AND analyzed_at > ?
            ORDER BY analyzed_at DESC
        """
    else:
        # Get analyzed decisions without embeddings
        query = f"""
            SELECT i.id
            FROM intimations i
            LEFT JOIN {table_name} e ON i.id = e.intimation_id
            WHERE i.analyzed = TRUE
              AND i.analyzed_at > ?
              AND e.intimation_id IS NULL
            ORDER BY i.analyzed_at DESC
        """

    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    result = con.con.execute(query, [cutoff_date])

    decision_ids = [row[0] for row in result.fetchall()]

    logger.info(
        "found_decisions_to_process",
        count=len(decision_ids),
        days_back=days_back,
        cutoff_date=cutoff_date.isoformat(),
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
    result = con.con.execute(query, [intimation_id])
    row = result.fetchone()

    if not row:
        logger.warning("decision_not_found", intimation_id=intimation_id)
        return ""

    return row[0] or ""


def save_stats(stats, args):
    """Save job statistics to file.

    Args:
        stats: BatchStats from pipeline.
        args: Command-line arguments.
    """
    stats_dir = Path("data/stats")
    stats_dir.mkdir(parents=True, exist_ok=True)

    stats_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "days_back": args.days_back,
        "max_concurrency": args.max_concurrency,
        "total_decisions": stats.total_decisions,
        "cached_decisions": stats.cached_decisions,
        "processed_decisions": stats.processed_decisions,
        "failed_decisions": stats.failed_decisions,
        "cache_hit_rate": stats.cache_hit_rate,
        "success_rate": stats.success_rate,
        "duration_seconds": stats.duration_seconds,
        "throughput": stats.throughput,
    }

    stats_file = stats_dir / f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    stats_file.write_text(json.dumps(stats_data, indent=2))

    logger.info("stats_saved", file=str(stats_file))


async def main():
    """Main entry point for daily embedding job."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for daily digest",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=1,
        help="Number of days to look back for unembedded decisions (default: 1)",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=10,
        help="Maximum concurrent API requests (default: 10)",
    )

    args = parser.parse_args()

    logger.info(
        "daily_job_started",
        days_back=args.days_back,
        max_concurrency=args.max_concurrency,
    )

    # Get decisions to process
    decision_ids = get_decisions_to_process(days_back=args.days_back)

    if not decision_ids:
        logger.info("no_decisions_to_process")
        # Create empty stats file
        from causaganha.pipeline.embedding_pipeline import BatchStats

        empty_stats = BatchStats(
            total_decisions=0,
            cached_decisions=0,
            processed_decisions=0,
            failed_decisions=0,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
        )
        save_stats(empty_stats, args)
        return

    # Create pipeline
    storage = EmbeddingStorage(get_connection("data/causaganha.duckdb"))
    pipeline = EmbeddingPipeline(
        model=JINA_V4_1024,
        max_concurrency=args.max_concurrency,
        storage=storage,
    )

    # Progress callback
    def log_progress(stats):
        logger.info(
            "progress",
            processed=stats.processed_decisions,
            total=stats.total_decisions,
            cache_hit_rate=f"{stats.cache_hit_rate:.1%}",
            throughput=f"{stats.throughput:.1f} dec/s",
        )

    # Process batch
    stats = await pipeline.process_batch(
        intimation_ids=decision_ids,
        text_loader=load_decision_text,
        progress_callback=log_progress,
        progress_interval=100,
    )

    logger.info(
        "daily_job_completed",
        total=stats.total_decisions,
        cached=stats.cached_decisions,
        processed=stats.processed_decisions,
        failed=stats.failed_decisions,
        cache_hit_rate=f"{stats.cache_hit_rate:.1%}",
        duration_seconds=f"{stats.duration_seconds:.1f}s",
        throughput=f"{stats.throughput:.1f} dec/s",
    )

    # Save statistics
    save_stats(stats, args)


if __name__ == "__main__":
    asyncio.run(main())
