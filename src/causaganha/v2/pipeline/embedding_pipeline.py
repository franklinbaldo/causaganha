"""Batch processing pipeline for generating and storing embeddings.

This module provides high-throughput embedding generation with:
- Automatic caching (skip already-embedded decisions)
- Parallel processing with rate limit respect
- Progress tracking and statistics
- Error handling and retry logic
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import structlog

from causaganha.v2.analysis.embedding_models import EmbeddingModel
from causaganha.v2.analysis.embedding_service import EmbeddingService
from causaganha.v2.analysis.text_chunker import TextChunker
from causaganha.v2.storage.embedding_storage import EmbeddingStorage


logger = structlog.get_logger()


@dataclass
class BatchStats:
    """Statistics for batch embedding processing."""

    total_decisions: int
    cached_decisions: int
    processed_decisions: int
    failed_decisions: int
    start_time: datetime
    end_time: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        if self.end_time is None:
            return (datetime.utcnow() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_decisions == 0:
            return 0.0
        return self.cached_decisions / self.total_decisions

    @property
    def success_rate(self) -> float:
        """Calculate success rate for processed decisions."""
        if self.processed_decisions == 0:
            return 1.0
        return (self.processed_decisions - self.failed_decisions) / self.processed_decisions

    @property
    def throughput(self) -> float:
        """Calculate decisions processed per second."""
        duration = self.duration_seconds
        if duration == 0:
            return 0.0
        return self.processed_decisions / duration


class EmbeddingPipeline:
    """Batch pipeline for generating and storing embeddings.

    Features:
    - Automatic caching (checks if embeddings exist before generating)
    - Parallel processing with configurable concurrency
    - Rate limit respect (via semaphore)
    - Progress callbacks
    - Error handling with statistics

    Example:
        # Create pipeline
        pipeline = EmbeddingPipeline(
            model=JINA_V4_1024,
            max_concurrency=10,  # Respect Jina's rate limits
        )

        # Define text loader
        def load_decision_text(intimation_id: int) -> str:
            # Load from database or API
            return fetch_decision_from_db(intimation_id)

        # Process batch
        stats = await pipeline.process_batch(
            intimation_ids=[123, 456, 789, ...],
            text_loader=load_decision_text,
        )

        print(f"Processed {stats.processed_decisions} decisions")
        print(f"Cache hit rate: {stats.cache_hit_rate:.1%}")
        print(f"Throughput: {stats.throughput:.1f} decisions/sec")
    """

    def __init__(
        self,
        model: EmbeddingModel,
        max_concurrency: int = 10,
        storage: EmbeddingStorage | None = None,
        service: EmbeddingService | None = None,
    ):
        """Initialize embedding pipeline.

        Args:
            model: EmbeddingModel to use for generation.
            max_concurrency: Maximum concurrent embedding requests (respect rate limits).
            storage: EmbeddingStorage instance. If None, creates new one.
            service: EmbeddingService instance. If None, creates new one.
        """
        self.model = model
        self.max_concurrency = max_concurrency
        self.storage = storage or EmbeddingStorage()
        self.service = service  # Created lazily in async context
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def _ensure_service(self):
        """Ensure embedding service is initialized (lazy async initialization)."""
        if self.service is None:
            self.service = await EmbeddingService.create(
                provider=self.model.provider,
                model=self.model,
            )

    async def process_one(
        self,
        intimation_id: int,
        text_loader: Callable[[int], str],
        force: bool = False,
    ) -> dict[str, any]:
        """Process a single decision.

        Args:
            intimation_id: Intimation ID to process.
            text_loader: Function to load decision text given intimation ID.
            force: Force regeneration even if cached.

        Returns:
            Dictionary with processing result (status, cached, error, etc.)
        """
        async with self.semaphore:  # Respect rate limits
            try:
                # Check cache first (unless force=True)
                if not force:
                    cached = self.storage.load_embeddings(intimation_id, self.model)
                    if cached:
                        logger.debug(
                            "embedding_cache_hit",
                            intimation_id=intimation_id,
                            model=self.model.name,
                        )
                        return {
                            "intimation_id": intimation_id,
                            "status": "cached",
                            "cached": True,
                            "error": None,
                        }

                # Load decision text
                text = text_loader(intimation_id)

                if not text or not text.strip():
                    logger.warning(
                        "empty_decision_text",
                        intimation_id=intimation_id,
                    )
                    return {
                        "intimation_id": intimation_id,
                        "status": "failed",
                        "cached": False,
                        "error": "Empty decision text",
                    }

                # Ensure service is initialized
                await self._ensure_service()

                # Generate embeddings with chunking
                embeddings = await self.service.embed_chunked_text(
                    text,
                    strategy="auto",
                )

                # Chunk text for storage
                chunker = TextChunker(max_tokens=self.model.max_tokens)
                text_chunks = chunker.chunk_text(text, strategy="auto")

                # Store embeddings
                self.storage.save_embeddings_batch(
                    intimation_id=intimation_id,
                    embeddings=embeddings,
                    model=self.model,
                    text_chunks=text_chunks,
                )

                logger.info(
                    "embedding_generated",
                    intimation_id=intimation_id,
                    num_chunks=len(embeddings),
                    model=self.model.name,
                )

                return {
                    "intimation_id": intimation_id,
                    "status": "success",
                    "cached": False,
                    "error": None,
                    "num_chunks": len(embeddings),
                }

            except Exception as e:
                logger.error(
                    "embedding_generation_failed",
                    intimation_id=intimation_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return {
                    "intimation_id": intimation_id,
                    "status": "failed",
                    "cached": False,
                    "error": str(e),
                }

    async def process_batch(
        self,
        intimation_ids: list[int],
        text_loader: Callable[[int], str],
        force: bool = False,
        progress_callback: Callable[[BatchStats], None] | None = None,
        progress_interval: int = 10,
    ) -> BatchStats:
        """Process a batch of decisions.

        Args:
            intimation_ids: List of intimation IDs to process.
            text_loader: Function to load decision text given intimation ID.
            force: Force regeneration even if cached.
            progress_callback: Optional callback for progress updates.
            progress_interval: Call progress callback every N decisions.

        Returns:
            BatchStats with processing statistics.

        Example:
            def my_progress(stats: BatchStats):
                print(f"Progress: {stats.processed_decisions}/{stats.total_decisions}")
                print(f"Cache hit rate: {stats.cache_hit_rate:.1%}")

            stats = await pipeline.process_batch(
                intimation_ids=[1, 2, 3, ...],
                text_loader=load_text,
                progress_callback=my_progress,
                progress_interval=10,
            )
        """
        start_time = datetime.utcnow()

        stats = BatchStats(
            total_decisions=len(intimation_ids),
            cached_decisions=0,
            processed_decisions=0,
            failed_decisions=0,
            start_time=start_time,
        )

        logger.info(
            "batch_processing_started",
            total_decisions=len(intimation_ids),
            model=self.model.name,
            max_concurrency=self.max_concurrency,
        )

        # Process all decisions in parallel (respecting semaphore)
        tasks = [
            self.process_one(intimation_id, text_loader, force=force)
            for intimation_id in intimation_ids
        ]

        # Gather results and update stats
        for i, result in enumerate(await asyncio.gather(*tasks)):
            if result["cached"]:
                stats.cached_decisions += 1
            elif result["status"] == "failed":
                stats.failed_decisions += 1

            stats.processed_decisions += 1

            # Progress callback
            if progress_callback and (i + 1) % progress_interval == 0:
                progress_callback(stats)

        stats.end_time = datetime.utcnow()

        logger.info(
            "batch_processing_complete",
            total=stats.total_decisions,
            cached=stats.cached_decisions,
            processed=stats.processed_decisions,
            failed=stats.failed_decisions,
            duration_seconds=stats.duration_seconds,
            throughput=stats.throughput,
            cache_hit_rate=stats.cache_hit_rate,
        )

        return stats


async def process_decisions_batch(
    intimation_ids: list[int],
    text_loader: Callable[[int], str],
    model: EmbeddingModel,
    max_concurrency: int = 10,
    force: bool = False,
) -> BatchStats:
    """Convenience function to process a batch of decisions.

    Args:
        intimation_ids: List of intimation IDs to process.
        text_loader: Function to load decision text given intimation ID.
        model: EmbeddingModel to use.
        max_concurrency: Maximum concurrent requests (respect rate limits).
        force: Force regeneration even if cached.

    Returns:
        BatchStats with processing statistics.

    Example:
        from causaganha.v2.analysis.embedding_models import JINA_V4_1024

        def load_text(intimation_id: int) -> str:
            # Load from database
            return get_decision_text_from_db(intimation_id)

        stats = await process_decisions_batch(
            intimation_ids=[123, 456, 789],
            text_loader=load_text,
            model=JINA_V4_1024,
            max_concurrency=10,
        )

        print(f"Done! Cache hit rate: {stats.cache_hit_rate:.1%}")
    """
    pipeline = EmbeddingPipeline(
        model=model,
        max_concurrency=max_concurrency,
    )

    return await pipeline.process_batch(
        intimation_ids=intimation_ids,
        text_loader=text_loader,
        force=force,
    )
