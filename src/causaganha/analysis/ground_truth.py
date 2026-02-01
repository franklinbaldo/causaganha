"""Ground truth management and synchronization."""

from typing import Any

import structlog
from ibis.backends.duckdb import Backend

from causaganha.analysis.embedding_service import EmbeddingService
from causaganha.analysis.vector_store import VectorStore


logger = structlog.get_logger()


class GroundTruthManager:
    """Manages ground truth synchronization and retrieval."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """Initialize GroundTruthManager.

        Args:
            vector_store: VectorStore instance.
            embedding_service: EmbeddingService instance.
        """
        self.vector_store = vector_store or VectorStore()
        self.embedding_service = embedding_service
        self.table_name = "ground_truth"

    async def _get_embedding_service(self) -> EmbeddingService:
        """Ensure embedding service is initialized."""
        if self.embedding_service is None:
            self.embedding_service = await EmbeddingService.create()
        return self.embedding_service

    def init_store(self, overwrite: bool = False) -> None:
        """Initialize the ground truth table in vector store.

        Args:
            overwrite: Whether to overwrite existing table.
        """
        if overwrite:
            self.vector_store.delete_table(self.table_name)

        if self.vector_store.table_exists(self.table_name):
            logger.info("ground_truth_table_already_exists")
            return

        # Create table with a dummy record to define schema
        # We use a zero vector for the embedding
        dummy_data = [
            {
                "vector": [0.0] * 1024,  # Default dimension for Jina v4
                "intimation_id": 0,
                "text": "Initial placeholder",
                "outcome": "UNKNOWN",
            },
        ]
        self.vector_store.create_table(self.table_name, dummy_data)
        logger.info("ground_truth_initialized")

    async def sync_from_db(
        self,
        con: Backend,
        min_confidence: float = 0.90,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Synchronize high-confidence analyses from DuckDB to vector store.

        Args:
            con: DuckDB connection.
            min_confidence: Minimum confidence score to include.
            limit: Maximum number of records to sync.

        Returns:
            Sync statistics.
        """
        logger.info(
            "ground_truth_sync_start",
            min_confidence=min_confidence,
            limit=limit,
        )

        # 1. Fetch data from DuckDB
        # We need intimation texts and their certified outcomes
        query = f"""
            SELECT
                i.id as intimation_id,
                i.texto as text,
                da.outcome as outcome
            FROM decision_analysis da
            JOIN intimations i ON da.intimation_id = i.id
            WHERE da.confidence_score >= {min_confidence}
              AND i.texto IS NOT NULL
              AND i.texto != ''
            LIMIT {limit}
        """

        records = con.con.execute(query).fetchall()

        if not records:
            logger.info("no_high_confidence_records_found")
            return {"synced": 0, "status": "no_data"}

        # 2. Get already synced IDs to avoid duplicates
        existing_ids = set()
        if self.vector_store.table_exists(self.table_name):
            table = self.vector_store.get_table(self.table_name)
            existing_records = table.to_pandas()
            if not existing_records.empty and "intimation_id" in existing_records.columns:
                existing_ids = set(existing_records["intimation_id"].tolist())

        # 3. Filter new records
        new_records = [r for r in records if r[0] not in existing_ids]

        if not new_records:
            logger.info("all_records_already_synced")
            return {"synced": 0, "status": "already_synced"}

        # 4. Generate embeddings and prepare for insertion
        embedding_service = await self._get_embedding_service()
        texts = [r[1] for r in new_records]

        logger.info("generating_embeddings_for_sync", count=len(texts))
        vectors = await embedding_service.embed_batch(
            texts,
            task_type="RETRIEVAL_DOCUMENT",
            add_prefix=True,
        )

        data_to_insert = []
        for i, (intimation_id, text, outcome) in enumerate(new_records):
            data_to_insert.append(
                {
                    "vector": vectors[i],
                    "intimation_id": intimation_id,
                    "text": text[:1000],  # Store snippet for reference
                    "outcome": outcome,
                },
            )

        # 5. Insert into LanceDB
        if not self.vector_store.table_exists(self.table_name):
            self.vector_store.create_table(self.table_name, data_to_insert)
        else:
            self.vector_store.add_documents(self.table_name, data_to_insert)

        logger.info("ground_truth_sync_complete", synced=len(data_to_insert))

        return {
            "synced": len(data_to_insert),
            "total_candidates": len(records),
            "status": "success",
        }

    async def search(self, query_text: str, k: int = 5) -> list[dict[str, Any]]:
        """Search for similar Ground Truth examples.

        Args:
            query_text: The text to search for.
            k: Number of results.

        Returns:
            List of matching records.
        """
        embedding_service = await self._get_embedding_service()
        query_vector = await embedding_service.embed_text(
            query_text,
            task_type="RETRIEVAL_QUERY",
            add_prefix=True,
        )

        return self.vector_store.search(self.table_name, query_vector, k=k)
