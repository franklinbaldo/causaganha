"""Embedding storage using Ibis/DuckDB for local processing and Parquet export.

This module handles:
1. Storing embeddings locally during processing (DuckDB)
2. Each model gets its own table (e.g., embeddings_jina_v4_1024, embeddings_google_gemini_768)
3. Exporting embeddings to Parquet for Internet Archive upload
4. Loading cached embeddings to avoid regeneration

Design:
- Separate table per model to avoid mixing incompatible embeddings
- Native FLOAT[] arrays (2-5x faster than JSON, enables similarity search)
- Vectorized operations for batch inserts (no iteration)
- Pandas DataFrames for bulk operations
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import structlog
from ibis.backends.duckdb import Backend

from causaganha.analysis.embedding_models import EmbeddingModel
from causaganha.storage.connection import get_connection


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

    # Create table with native FLOAT array (much faster than JSON)
    con.raw_sql(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            texto_id VARCHAR NOT NULL,
            chunk_index INTEGER NOT NULL,

            -- Embedding data (native FLOAT array, fixed dimension for this table)
            embedding FLOAT[{model.dimension}] NOT NULL,

            -- Versioning
            embedding_version VARCHAR(20) DEFAULT '1.0',
            api_version VARCHAR(20) DEFAULT NULL,

            -- Metadata
            text_preview TEXT,
            created_at TIMESTAMP DEFAULT NOW(),

            PRIMARY KEY (texto_id, chunk_index)
        );

        -- Index for lookups
        CREATE INDEX IF NOT EXISTS idx_{table_name}_texto
            ON {table_name}(texto_id);

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

    def __init__(self, con: Backend | None = None) -> None:
        """Initialize embedding storage.

        Args:
            con: Ibis connection. If None, uses default connection.
        """
        self.con = con or get_connection()

    def save_embeddings_batch(
        self,
        texto_id: str,
        embeddings: list[list[float]],
        model: EmbeddingModel,
        text_chunks: list[str] | None = None,
    ) -> None:
        """Save multiple embeddings (chunks) for one document using vectorized operation.

        Args:
            texto_id: Content-addressed text ID (UUIDv5).
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
            msg = (
                f"Embedding dimension mismatch: expected {model.dimension}, "
                f"got {set(dims)} for model {model.name}"
            )
            raise ValueError(
                msg,
            )

        # Prepare data using vectorized operations (pandas DataFrame)
        num_chunks = len(embeddings)

        data = {
            "texto_id": [texto_id] * num_chunks,
            "chunk_index": list(range(num_chunks)),
            "embedding": embeddings,  # Native list → FLOAT[] (no JSON conversion needed!)
            "embedding_version": ["1.0"] * num_chunks,
            "api_version": [None] * num_chunks,
            "text_preview": [
                (text_chunks[i][:200] if text_chunks and i < len(text_chunks) else "")
                for i in range(num_chunks)
            ],
            "created_at": [datetime.utcnow()] * num_chunks,
        }

        embeddings_frame = pd.DataFrame(data)

        # Bulk insert using DuckDB's efficient INSERT from DataFrame
        # Native FLOAT[] arrays are 2-5x faster than JSON

        # Delete existing embeddings for this text
        self.con.con.execute(
            f"DELETE FROM {table_name} WHERE texto_id = ?",
            [texto_id],
        )

        # Register DataFrame and insert
        self.con.con.register("temp_embeddings", embeddings_frame)
        self.con.con.execute(
            f"INSERT INTO {table_name} SELECT * FROM temp_embeddings",
        )
        self.con.con.unregister("temp_embeddings")

        logger.info(
            "embeddings_batch_saved",
            texto_id=texto_id,
            num_chunks=len(embeddings),
            table=table_name,
        )

    def load_embeddings(
        self,
        texto_id: str,
        model: EmbeddingModel,
    ) -> list[dict[str, Any]] | None:
        """Load embeddings for a document using vectorized query.

        Args:
            texto_id: Content-addressed text ID (UUIDv5).
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
                texto_id=texto_id,
            )
            return None

        # Get table reference
        table = self.con.table(table_name)

        # Query for this text (vectorized)
        query = table.filter(table.texto_id == texto_id).order_by(table.chunk_index)

        # Execute and fetch
        results = query.execute()

        if results.empty:
            logger.debug(
                "embeddings_not_found",
                texto_id=texto_id,
                table=table_name,
            )
            return None

        # Convert native FLOAT[] arrays to Python lists (no JSON parsing needed!)
        # DuckDB returns arrays as Python lists directly
        results["embedding"] = results["embedding"].apply(list)

        # Convert to list of dicts (using pandas built-in vectorization)
        embeddings = results[["chunk_index", "embedding", "text_preview", "created_at"]].to_dict(
            orient="records",
        )

        logger.debug(
            "embeddings_loaded",
            texto_id=texto_id,
            num_chunks=len(embeddings),
            table=table_name,
        )

        return embeddings

    def export_to_parquet(
        self,
        output_path: str | Path,
        model: EmbeddingModel,
        texto_id: str | None = None,
    ) -> Path:
        """Export embeddings to Parquet file for Internet Archive upload.

        Uses vectorized Ibis query to export directly to Parquet (no Python iteration).

        Args:
            output_path: Path to save Parquet file.
            model: EmbeddingModel to export (determines which table to query).
            texto_id: Optional filter by text ID.

        Returns:
            Path to the exported Parquet file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        table_name = _get_table_name(model)

        # Check if table exists
        if table_name not in self.con.list_tables():
            msg = (
                f"No embeddings table found for model {model.name} ({model.dimension}D). "
                f"Expected table: {table_name}"
            )
            raise ValueError(
                msg,
            )

        # Get table reference
        table = self.con.table(table_name)
        query = table

        # Apply filter
        if texto_id is not None:
            query = query.filter(table.texto_id == texto_id)

        # Order by using the table columns directly
        query = query.order_by([table.texto_id, table.chunk_index])

        # Export to Parquet (vectorized - no Python iteration)
        export_frame = query.execute()

        if export_frame.empty:
            logger.warning(
                "export_no_data",
                output_path=str(output_path),
                table=table_name,
                texto_id=texto_id,
            )
            msg = f"No embeddings found in table {table_name}"
            raise ValueError(msg)

        # Write to Parquet with compression (single vectorized operation)
        # ZSTD provides best compression ratio for archival storage
        export_frame.to_parquet(
            output_path,
            index=False,
            engine="pyarrow",
            compression="zstd",  # Best compression for Internet Archive
            compression_level=9,  # Maximum compression (slower but smallest size)
        )

        # Calculate compression stats
        file_size = output_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        logger.info(
            "embeddings_exported",
            output_path=str(output_path),
            num_rows=len(export_frame),
            file_size_mb=round(file_size_mb, 2),
            table=table_name,
            texto_id=texto_id,
            compression="zstd",
        )

        return output_path

    def find_similar_texts(
        self,
        query_embedding: list[float],
        model: EmbeddingModel,
        top_k: int = 10,
        min_similarity: float = 0.7,
        exclude_texto_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar texts using cosine similarity.

        Uses DuckDB's native list_cosine_similarity for fast vector search.

        Args:
            query_embedding: Query embedding vector.
            model: EmbeddingModel to search in.
            top_k: Number of top results to return.
            min_similarity: Minimum similarity threshold (0-1).
            exclude_texto_ids: Optional list of texto IDs to exclude.

        Returns:
            List of similar texts with similarity scores.
        """
        table_name = _get_table_name(model)

        # Check if table exists
        if table_name not in self.con.list_tables():
            msg = f"No embeddings table found for model {model.name} ({model.dimension}D)"
            raise ValueError(
                msg,
            )

        # Validate query embedding dimension
        if len(query_embedding) != model.dimension:
            msg = (
                f"Query embedding dimension mismatch: expected {model.dimension}, "
                f"got {len(query_embedding)}"
            )
            raise ValueError(
                msg,
            )

        # Get table reference
        self.con.table(table_name)

        # Build exclusion filter
        exclusion_sql = ""
        if exclude_texto_ids:
            placeholders = ",".join(f"'{tid}'" for tid in exclude_texto_ids)
            exclusion_sql = f"AND texto_id NOT IN ({placeholders})"

        # Use DuckDB's native list_cosine_similarity for fast vector search
        # Query only chunk_index=0 to get one result per text
        query_sql = f"""
            SELECT
                texto_id,
                chunk_index,
                list_cosine_similarity(embedding, ?::FLOAT[{model.dimension}]) as similarity,
                text_preview,
                created_at
            FROM {table_name}
            WHERE chunk_index = 0  -- Only first chunk per text
                {exclusion_sql}
                AND list_cosine_similarity(embedding, ?::FLOAT[{model.dimension}]) >= ?
            ORDER BY similarity DESC
            LIMIT ?
        """

        # Execute query
        result = self.con.con.execute(
            query_sql,
            [query_embedding, query_embedding, min_similarity, top_k],
        )

        # Fetch results
        rows = result.fetchall()

        # Convert to list of dicts
        similar_texts = []
        for row in rows:
            similar_texts.append(
                {
                    "texto_id": row[0],
                    "chunk_index": row[1],
                    "similarity": float(row[2]),
                    "text_preview": row[3],
                    "created_at": row[4],
                },
            )

        logger.info(
            "similarity_search_complete",
            table=table_name,
            query_dim=len(query_embedding),
            results_found=len(similar_texts),
            top_k=top_k,
            min_similarity=min_similarity,
        )

        return similar_texts

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

            # Get unique texts (vectorized)
            unique_texts = table.select("texto_id").distinct().count().execute()

            models.append(
                {
                    "table_name": table_name,
                    "total_embeddings": int(count),
                    "unique_texts": int(unique_texts),
                },
            )

        return models

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about stored embeddings (vectorized aggregation).

        Returns:
            Dictionary with stats (total_embeddings, models, etc.)
        """
        models = self.list_models()

        # Vectorized sum using pandas
        total_embeddings = sum(m["total_embeddings"] for m in models)
        unique_texts = sum(m["unique_texts"] for m in models)

        return {
            "total_embeddings": total_embeddings,
            "unique_texts": unique_texts,
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
