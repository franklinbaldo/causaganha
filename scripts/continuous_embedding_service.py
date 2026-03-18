"""Continuous embedding generation service for Cloud Run.

This service runs 24/7 and continuously processes unembedded decisions.
Designed for deployment on Google Cloud Run as a long-running job.

Usage:
    # Local testing
    uv run python scripts/continuous_embedding_service.py

    # Deploy to Cloud Run
    gcloud run deploy causaganha-embeddings \
        --source . \
        --region us-central1 \
        --cpu 2 \
        --memory 4Gi \
        --min-instances 1 \
        --max-instances 1 \
        --timeout 3600
"""

import asyncio
import time
from datetime import datetime

import structlog

from causaganha.analysis.embedding_models import JINA_V4_1024
from causaganha.pipeline.embedding_pipeline import EmbeddingPipeline
from causaganha.storage.connection import get_connection
from causaganha.storage.embedding_storage import EmbeddingStorage


logger = structlog.get_logger()


def get_unembedded_decisions(
    storage: EmbeddingStorage,
    model,
    limit: int = 100,
) -> list[int]:
    """Get decisions that don't have embeddings yet.

    Args:
        storage: EmbeddingStorage instance.
        model: EmbeddingModel to check.
        limit: Maximum decisions to return.

    Returns:
        List of intimation IDs that need embeddings.
    """
    table_name = f"embeddings_{model.provider}_{model.name.replace('-', '_')}_{model.dimension}"

    # Get all analyzed decisions without embeddings
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
        con = storage.con
        result = con.con.execute(query, [limit])
        rows = result.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        logger.exception("failed_to_get_unembedded_decisions", error=str(e))
        return []


def load_decision_text(intimation_id: int) -> str:
    """Load decision text from database.

    Args:
        intimation_id: Intimation ID.

    Returns:
        Decision text.
    """
    # This should load from your actual database
    # For now, stub implementation
    con = get_connection()

    query = """
        SELECT texto
        FROM intimations
        WHERE id = ?
    """

    try:
        result = con.con.execute(query, [intimation_id])
        row = result.fetchone()
        return row[0] if row else ""
    except Exception as e:
        logger.exception(
            "failed_to_load_decision_text",
            intimation_id=intimation_id,
            error=str(e),
        )
        return ""


async def process_batch_with_retry(
    pipeline: EmbeddingPipeline,
    intimation_ids: list[int],
    max_retries: int = 3,
):
    """Process a batch with exponential backoff retry.

    Args:
        pipeline: EmbeddingPipeline instance.
        intimation_ids: List of intimation IDs.
        max_retries: Maximum retry attempts.
    """
    for attempt in range(max_retries):
        try:
            stats = await pipeline.process_batch(
                intimation_ids=intimation_ids,
                text_loader=load_decision_text,
            )

            logger.info(
                "batch_complete",
                total=stats.total_decisions,
                cached=stats.cached_decisions,
                processed=stats.processed_decisions,
                failed=stats.failed_decisions,
                cache_hit_rate=stats.cache_hit_rate,
                throughput=stats.throughput,
            )
        except Exception as e:
            wait_time = 2**attempt  # Exponential backoff
            logger.exception(
                "batch_failed",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e),
                wait_seconds=wait_time,
            )

            if attempt < max_retries - 1:
                await asyncio.sleep(wait_time)
            else:
                logger.exception("batch_failed_permanently", error=str(e))
                raise
        else:
            return stats
    return None


async def continuous_processing_loop(
    batch_size: int = 100,
    max_concurrency: int = 20,
    idle_sleep_seconds: int = 300,
) -> None:
    """Main continuous processing loop.

    Args:
        batch_size: Decisions to process per batch.
        max_concurrency: Max concurrent embedding requests.
        idle_sleep_seconds: Seconds to sleep when no work available.
    """
    logger.info(
        "continuous_service_starting",
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        idle_sleep_seconds=idle_sleep_seconds,
    )

    # Initialize storage and pipeline
    storage = EmbeddingStorage()
    pipeline = EmbeddingPipeline(
        model=JINA_V4_1024,
        max_concurrency=max_concurrency,
        storage=storage,
    )

    iterations = 0
    total_processed = 0

    while True:
        iterations += 1
        iteration_start = time.time()

        logger.info(
            "iteration_starting",
            iteration=iterations,
            total_processed=total_processed,
        )

        # Get next batch of unembedded decisions
        intimation_ids = get_unembedded_decisions(
            storage=storage,
            model=JINA_V4_1024,
            limit=batch_size,
        )

        if not intimation_ids:
            logger.info(
                "no_work_available",
                sleep_seconds=idle_sleep_seconds,
            )
            await asyncio.sleep(idle_sleep_seconds)
            continue

        logger.info(
            "batch_starting",
            batch_size=len(intimation_ids),
            intimation_ids=intimation_ids[:10],  # Log first 10
        )

        # Process batch
        try:
            stats = await process_batch_with_retry(
                pipeline=pipeline,
                intimation_ids=intimation_ids,
            )

            total_processed += stats.processed_decisions

        except Exception as e:
            logger.exception("iteration_failed", error=str(e))

        iteration_duration = time.time() - iteration_start

        logger.info(
            "iteration_complete",
            iteration=iterations,
            duration_seconds=round(iteration_duration, 2),
            total_processed=total_processed,
        )

        # Small sleep between iterations to avoid hammering DB
        await asyncio.sleep(5)


def main() -> None:
    """Entry point for continuous embedding service."""
    # Configuration from environment variables
    import os

    batch_size = int(os.getenv("BATCH_SIZE", "100"))
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "20"))
    idle_sleep = int(os.getenv("IDLE_SLEEP_SECONDS", "300"))

    logger.info(
        "service_starting",
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        idle_sleep_seconds=idle_sleep,
        timestamp=datetime.utcnow().isoformat(),
    )

    # Run continuous loop
    asyncio.run(
        continuous_processing_loop(
            batch_size=batch_size,
            max_concurrency=max_concurrency,
            idle_sleep_seconds=idle_sleep,
        ),
    )


if __name__ == "__main__":
    main()
