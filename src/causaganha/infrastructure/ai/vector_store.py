"""Vector store using LanceDB for decision embeddings."""
import os
from pathlib import Path
from typing import Any

import lancedb
import google.generativeai as genai
import numpy as np
import pandas as pd
import structlog
from lancedb.pydantic import LanceModel, Vector


logger = structlog.get_logger()


class DecisionEmbedding(LanceModel):
    """Schema for decision embeddings in LanceDB."""

    intimation_id: int
    chunk_index: int
    chunk_text: str
    vector: Vector(768)  # Gemini embedding dimension (768 for compatibility with old data)
    chunk_size: int
    created_at: str


class DecisionVectorStore:
    """Manage decision embeddings using LanceDB."""

    def __init__(
        self,
        db_path: str = "data/lancedb",
        table_name: str = "decision_embeddings",
        api_key: str | None = None,
    ):
        """Initialize the vector store.

        Args:
            db_path: Path to LanceDB database
            table_name: Name of the table for embeddings
            api_key: Optional Gemini API key
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        self.db = lancedb.connect(str(self.db_path))
        self.table_name = table_name

        # Configure Gemini
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY required")

        genai.configure(api_key=key)
        # Updated to current model (text-embedding-004 was deprecated August 2025)
        # Using 768 dimension for compatibility with existing LanceDB schema
        self.model_name = "models/gemini-embedding-001"
        self.dimension = 768  # Compatible with DecisionEmbedding schema

        logger.info("vector_store_initialized", db_path=str(self.db_path))

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (768 dimensions for compatibility)
        """
        result = genai.embed_content(
            model=self.model_name,
            content=text,
            task_type="retrieval_document",
            output_dimensionality=self.dimension,  # Force 768D for LanceDB compatibility
        )
        return result["embedding"]

    def chunk_text(
        self, text: str, chunk_size: int = 500, overlap: int = 100
    ) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind(".")
                if last_period > chunk_size * 0.7:
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    def index_decision(
        self,
        intimation_id: int,
        text: str,
        chunk_size: int = 500,
        overlap: int = 100,
    ) -> int:
        """Index a decision by chunking and embedding.

        Args:
            intimation_id: ID of the intimation
            text: Decision text
            chunk_size: Size of chunks
            overlap: Overlap between chunks

        Returns:
            Number of chunks indexed
        """
        logger.info("indexing_decision", intimation_id=intimation_id, text_length=len(text))

        # Chunk the text
        chunks = self.chunk_text(text, chunk_size=chunk_size, overlap=overlap)

        # Create embeddings
        records = []
        for i, chunk in enumerate(chunks):
            embedding = self._get_embedding(chunk)

            records.append(
                {
                    "intimation_id": intimation_id,
                    "chunk_index": i,
                    "chunk_text": chunk,
                    "vector": embedding,
                    "chunk_size": len(chunk),
                    "created_at": pd.Timestamp.now().isoformat(),
                }
            )

        # Add to LanceDB
        if self.table_name in self.db.table_names():
            table = self.db.open_table(self.table_name)
            table.add(records)
        else:
            table = self.db.create_table(self.table_name, data=records, mode="overwrite")

        logger.info("decision_indexed", intimation_id=intimation_id, chunks=len(chunks))
        return len(chunks)

    def batch_index_decisions(
        self,
        decisions: list[dict[str, Any]],
        chunk_size: int = 500,
    ) -> dict[str, int]:
        """Batch index multiple decisions.

        Args:
            decisions: List of dicts with 'intimation_id' and 'text'
            chunk_size: Size of chunks

        Returns:
            Stats about indexing
        """
        total_chunks = 0
        for decision in decisions:
            chunks = self.index_decision(
                intimation_id=decision["intimation_id"],
                text=decision["text"],
                chunk_size=chunk_size,
            )
            total_chunks += chunks

        return {
            "decisions_indexed": len(decisions),
            "total_chunks": total_chunks,
            "avg_chunks_per_decision": total_chunks / len(decisions) if decisions else 0,
        }

    def search_similar(
        self, query_text: str, limit: int = 10
    ) -> pd.DataFrame:
        """Search for similar chunks.

        Args:
            query_text: Query text
            limit: Number of results

        Returns:
            DataFrame with similar chunks
        """
        query_embedding = self._get_embedding(query_text)

        table = self.db.open_table(self.table_name)
        results = table.search(query_embedding).limit(limit).to_pandas()

        return results

    def analyze_decision_by_similarity(
        self, text: str, reference_queries: dict[str, list[str]], top_k: int = 5
    ) -> dict[str, Any]:
        """Analyze decision outcome by comparing with reference queries.

        Args:
            text: Decision text to analyze
            reference_queries: Dict mapping outcome -> list of reference phrases
            top_k: Number of top results to consider

        Returns:
            Analysis result with outcome and confidence
        """
        logger.info("analyzing_with_similarity", text_length=len(text))

        # First, temporarily index this decision
        temp_id = -1
        self.index_decision(temp_id, text)

        # Search for each reference phrase and aggregate scores
        outcome_scores: dict[str, list[float]] = {
            outcome: [] for outcome in reference_queries.keys()
        }

        for outcome, queries in reference_queries.items():
            for query in queries:
                results = self.search_similar(query, limit=top_k)

                # Filter only chunks from our temp decision
                temp_results = results[results["intimation_id"] == temp_id]

                if not temp_results.empty:
                    # Get similarity scores (LanceDB returns _distance, lower is better)
                    # Convert distance to similarity
                    if "_distance" in temp_results.columns:
                        similarities = 1 / (1 + temp_results["_distance"])
                        outcome_scores[outcome].extend(similarities.tolist())

        # Calculate final scores (max similarity for each outcome)
        final_scores = {
            outcome: max(scores) if scores else 0.0
            for outcome, scores in outcome_scores.items()
        }

        # Clean up temp data
        table = self.db.open_table(self.table_name)
        # Note: LanceDB doesn't have easy delete, we'll mark it differently in production

        best_outcome = max(final_scores, key=final_scores.get)  # type: ignore
        confidence = final_scores[best_outcome]

        logger.info("similarity_analysis_complete", outcome=best_outcome, confidence=confidence)

        return {
            "outcome": best_outcome,
            "confidence": confidence,
            "all_scores": final_scores,
            "method": "vector_similarity_lancedb",
        }

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the vector store.

        Returns:
            Stats dictionary
        """
        if self.table_name not in self.db.table_names():
            return {"indexed_decisions": 0, "total_chunks": 0}

        table = self.db.open_table(self.table_name)
        df = table.to_pandas()

        unique_intimations = df["intimation_id"].nunique()
        total_chunks = len(df)

        return {
            "indexed_decisions": unique_intimations,
            "total_chunks": total_chunks,
            "avg_chunks_per_decision": total_chunks / unique_intimations if unique_intimations > 0 else 0,
        }
