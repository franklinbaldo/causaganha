"""Embedding storage using Ibis/DuckDB for local processing and Parquet export.

This module handles:
1. Storing embeddings locally during processing (DuckDB)
2. Each model gets its own table (e.g., embeddings_jina_v4_1024, embeddings_google_gemini_768)
3. Exporting embeddings to Parquet for Internet Archive upload
4. Loading cached embeddings to avoid regeneration

Design:
- Separate table per model to avoid mixing incompatible embeddings
- Vectorized operations for batch inserts (no iteration)
- Pandas DataFrames for bulk operations
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import structlog
from ibis.backends.duckdb import Backend

from causaganha.v2.analysis.embedding_models import EmbeddingModel
from causaganha.v2.storage.connection import get_connection

logger = structlog.get_logger()


def _get_table_name(model: EmbeddingModel) -> str:
    """Generate table name for a model.

    Format: embeddings_{provider}_{model}_{dimension}
    Example: embeddings_jina_v4_1024, embeddings_google_gemini_768

    Args:
        model: EmbeddingModel to generate table name for.

    Returns:
        Table name (safe for SQL).
    """
    # Sanitize model name (replace hyphens with underscores, remove special chars)
    safe_model = re.sub(r"[^a-z0-9_]", "_", model.name.lower().replace("-", "_"))

    # Shorten common model names
    safe_model = safe_model.replace("embeddings", "").replace("embedding", "").strip("_")

    return f"embeddings_{model.provider}_{safe_model}_{model.dimension}"


def _create_table_for_model(con: Backend, model: EmbeddingModel) -> str:
    """Create embeddings table for a specific model.

    Each model gets its own table to avoid mixing incompatible embeddings.

    Args:
        con: Ibis connection.
        model: EmbeddingModel to create table for.

    Returns:
        Table name created.
    """
    table_name = _get_table_name(model)

    # Check if table exists
    if table_name in con.list_tables():
        logger.debug("embeddings_table_exists", table=table_name)
        return table_name

    logger.info(
        "creating_embeddings_table",
        table=table_name,
        model=model.name,
        dimension=model.dimension,
    )

    # Create table
    con.raw_sql(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            intimation_id BIGINT NOT NULL,
            chunk_index INTEGER NOT NULL,

            -- Embedding data (fixed dimension for this table)
            embedding TEXT NOT NULL,  -- JSON array of floats

            -- Metadata
            text_preview TEXT,
            created_at TIMESTAMP DEFAULT NOW(),

            PRIMARY KEY (intimation_id, chunk_index)
        );

        -- Index for lookups
        CREATE INDEX IF NOT EXISTS idx_{table_name}_intimation
            ON {table_name}(intimation_id);

        -- Index for created_at (for cleanup/archival)
        CREATE INDEX IF NOT EXISTS idx_{table_name}_created
            ON {table_name}(created_at);
    """)

    logger.info("embeddings_table_created", table=table_name)

    return table_name


class EmbeddingStorage:
    """Store and retrieve embeddings using Ibis/DuckDB.

    Each model gets its own table to avoid mixing incompatible embeddings.
    Table names follow the pattern: embeddings_{provider}_{model}_{dimension}

    Uses vectorized operations for performance (no Python iteration).

    Examples:
        - embeddings_jina_v4_1024
        - embeddings_jina_v4_768
        - embeddings_google_gemini_768
    """

    def __init__(self, con: Backend | None = None):
        """Initialize embedding storage.

        Args:
            con: Ibis connection. If None, uses default connection.
        """
        self.con = con or get_connection()

    def save_embeddings_batch(
        self,
        intimation_id: int,
        embeddings: list[list[float]],
        model: EmbeddingModel,
        text_chunks: list[str] | None = None,
    ) -> None:
        """Save multiple embeddings (chunks) for one document using vectorized operation.

        Args:
            intimation_id: Intimation ID this embedding belongs to.
            embeddings: List of embedding vectors (one per chunk).
            model: EmbeddingModel that generated these embeddings.
            text_chunks: Optional list of text chunks (for preview).

        Raises:
            ValueError: If embedding dimension doesn't match model dimension.
        """
        # Ensure table exists
        table_name = _create_table_for_model(self.con, model)

        # Validate dimensions (vectorized check)
        dims = [len(emb) for emb in embeddings]
        if any(d != model.dimension for d in dims):
            raise ValueError(
                f"Embedding dimension mismatch: expected {model.dimension}, "
                f"got {set(dims)} for model {model.name}"
            )

        # Prepare data using vectorized operations (pandas DataFrame)
        num_chunks = len(embeddings)

        data = {
            "intimation_id": [intimation_id] * num_chunks,
            "chunk_index": list(range(num_chunks)),
            "embedding": [json.dumps(emb) for emb in embeddings],  # Vectorized JSON conversion
            "text_preview": [
                (text_chunks[i][:200] if text_chunks and i < len(text_chunks) else "")
                for i in range(num_chunks)
            ],
            "created_at": [datetime.utcnow()] * num_chunks,
        }

        df = pd.DataFrame(data)

        # Bulk insert using DuckDB's efficient INSERT from DataFrame
        # This is much faster than row-by-row inserts
        self.con.raw_sql(f"DELETE FROM {table_name} WHERE intimation_id = ?", [intimation_id])
        self.con.con.register("temp_embeddings", df)
        self.con.raw_sql(f"""
            INSERT INTO {table_name}
            SELECT * FROM temp_embeddings
        """)

        logger.info(
            "embeddings_batch_saved",
            intimation_id=intimation_id,
            num_chunks=len(embeddings),
            table=table_name,
        )

    def load_embeddings(
        self,
        intimation_id: int,
        model: EmbeddingModel,
    ) -> list[dict[str, Any]] | None:
        """Load embeddings for a document using vectorized query.

        Args:
            intimation_id: Intimation ID to load embeddings for.
            model: EmbeddingModel to load (determines which table to query).

        Returns:
            List of embedding records (with chunk_index, embedding, etc.) or None if not found.
        """
        table_name = _get_table_name(model)

        # Check if table exists
        if table_name not in self.con.list_tables():
            logger.debug(
                "embeddings_table_not_found",
                table=table_name,
                intimation_id=intimation_id,
            )
            return None

        # Get table reference
        table = self.con.table(table_name)

        # Query for this intimation (vectorized)
        query = (
            table
            .filter(table.intimation_id == intimation_id)
            .order_by(table.chunk_index)
        )

        # Execute and fetch
        results = query.execute()

        if results.empty:
            logger.debug(
                "embeddings_not_found",
                intimation_id=intimation_id,
                table=table_name,
            )
            return None

        # Vectorized JSON parsing using pandas apply
        results["embedding_vec"] = results["embedding"].apply(json.loads)

        # Convert to list of dicts (using pandas built-in vectorization)
        embeddings = results[["chunk_index", "embedding_vec", "text_preview", "created_at"]].to_dict(
            orient="records"
        )

        # Rename embedding_vec to embedding
        for emb in embeddings:
            emb["embedding"] = emb.pop("embedding_vec")

        logger.debug(
            "embeddings_loaded",
            intimation_id=intimation_id,
            num_chunks=len(embeddings),
            table=table_name,
        )

        return embeddings

    def export_to_parquet(
        self,
        output_path: str | Path,
        model: EmbeddingModel,
        intimation_id: int | None = None,
    ) -> Path:
        """Export embeddings to Parquet file for Internet Archive upload.

        Uses vectorized Ibis query to export directly to Parquet (no Python iteration).

        Args:
            output_path: Path to save Parquet file.
            model: EmbeddingModel to export (determines which table to query).
            intimation_id: Optional filter by intimation ID.

        Returns:
            Path to the exported Parquet file.

        Example:
            # Export all Jina v4 1024D embeddings
            storage.export_to_parquet(
                "embeddings_jina_v4_1024.parquet",
                model=JINA_V4_1024
            )

            # Export embeddings for specific intimation
            storage.export_to_parquet(
                "intimation_12345_embeddings.parquet",
                model=JINA_V4_1024,
                intimation_id=12345
            )
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        table_name = _get_table_name(model)

        # Check if table exists
        if table_name not in self.con.list_tables():
            raise ValueError(
                f"No embeddings table found for model {model.name} ({model.dimension}D). "
                f"Expected table: {table_name}"
            )

        # Get table reference
        table = self.con.table(table_name)

        # Build query (vectorized filtering)
        query = table

        # Apply filter
        if intimation_id is not None:
            query = query.filter(table.intimation_id == intimation_id)

        # Order by intimation_id and chunk_index
        query = query.order_by([table.intimation_id, table.chunk_index])

        # Export to Parquet (vectorized - no Python iteration)
        df = query.execute()

        if df.empty:
            logger.warning(
                "export_no_data",
                output_path=str(output_path),
                table=table_name,
                intimation_id=intimation_id,
            )
            raise ValueError(f"No embeddings found in table {table_name}")

        # Write to Parquet (single vectorized operation)
        df.to_parquet(output_path, index=False, engine="pyarrow")

        logger.info(
            "embeddings_exported",
            output_path=str(output_path),
            num_rows=len(df),
            table=table_name,
            intimation_id=intimation_id,
        )

        return output_path

    def list_models(self) -> list[dict[str, Any]]:
        """List all models that have embeddings stored (vectorized aggregation).

        Returns:
            List of models with metadata (table_name, row_count, etc.)
        """
        tables = self.con.list_tables()

        # Filter to embedding tables only
        embedding_tables = [t for t in tables if t.startswith("embeddings_")]

        models = []
        for table_name in embedding_tables:
            # Get row count (vectorized)
            table = self.con.table(table_name)
            count = table.count().execute()

            # Get unique intimations (vectorized)
            unique_intimations = table.select("intimation_id").distinct().count().execute()

            models.append({
                "table_name": table_name,
                "total_embeddings": int(count),
                "unique_intimations": int(unique_intimations),
            })

        return models

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about stored embeddings (vectorized aggregation).

        Returns:
            Dictionary with stats (total_embeddings, models, etc.)
        """
        models = self.list_models()

        # Vectorized sum using pandas
        total_embeddings = sum(m["total_embeddings"] for m in models)
        unique_intimations = sum(m["unique_intimations"] for m in models)

        return {
            "total_embeddings": total_embeddings,
            "unique_intimations": unique_intimations,
            "models": models,
        }


def get_embedding_storage(con: Backend | None = None) -> EmbeddingStorage:
    """Get embedding storage instance.

    Args:
        con: Ibis connection. If None, uses default connection.

    Returns:
        EmbeddingStorage instance.
    """
    return EmbeddingStorage(con=con)
