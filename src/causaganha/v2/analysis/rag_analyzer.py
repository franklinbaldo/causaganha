"""RAG-based decision analyzer using vector similarity search."""

import os
from collections import Counter
from pathlib import Path
from typing import Any

import structlog

from causaganha.v2.analysis.embedding_service import EmbeddingService
from causaganha.v2.analysis.models import DecisionAnalysis
from causaganha.v2.analysis.vector_store import VectorStore

logger = structlog.get_logger()

# Constants
DEFAULT_K_NEIGHBORS = 7
DEFAULT_CONFIDENCE_THRESHOLD = 0.70
DEFAULT_GROUND_TRUTH_TABLE = "ground_truth"
COST_PER_DECISION = 0.000008  # Approximate cost for RAG analysis


class RAGAnalyzer:
    """Analyze judicial decisions using RAG (Retrieval-Augmented Generation)."""

    def __init__(
        self,
        vector_store_path: str | Path = "data/lancedb",
        ground_truth_table: str = DEFAULT_GROUND_TRUTH_TABLE,
        k_neighbors: int = DEFAULT_K_NEIGHBORS,
        api_key: str | None = None,
    ) -> None:
        """Initialize the RAG analyzer.

        Args:
            vector_store_path: Path to LanceDB database.
            ground_truth_table: Name of the ground truth table.
            k_neighbors: Number of nearest neighbors for k-NN classification.
            api_key: Google API key for embeddings. If None, reads from env.
        """
        self.vector_store = VectorStore(db_path=vector_store_path)
        self.embedding_service = EmbeddingService(api_key=api_key)
        self.ground_truth_table = ground_truth_table
        self.k_neighbors = k_neighbors

        # Verify ground truth table exists
        if not self.vector_store.table_exists(ground_truth_table):
            logger.warning(
                "ground_truth_table_not_found",
                table=ground_truth_table,
                path=str(vector_store_path),
            )

        logger.info(
            "rag_analyzer_initialized",
            vector_store_path=str(vector_store_path),
            ground_truth_table=ground_truth_table,
            k_neighbors=k_neighbors,
        )

    async def analyze_text(
        self,
        text: str,
        intimation_id: int | None = None,
    ) -> DecisionAnalysis:
        """Analyze a decision text using RAG.

        Args:
            text: The decision text to analyze.
            intimation_id: Optional intimation ID for logging.

        Returns:
            DecisionAnalysis with classification result.

        Raises:
            ValueError: If ground truth table doesn't exist.
        """
        if not self.vector_store.table_exists(self.ground_truth_table):
            raise ValueError(
                f"Ground truth table '{self.ground_truth_table}' not found. "
                "Please initialize ground truth first."
            )

        logger.info(
            "rag_analysis_start",
            intimation_id=intimation_id,
            text_length=len(text),
        )

        try:
            # Step 1: Chunk the text
            chunks = self.embedding_service.chunk_text(text)
            logger.debug("text_chunked", num_chunks=len(chunks))

            # Step 2: Generate embeddings for all chunks
            embeddings = await self.embedding_service.embed_batch(
                chunks,
                task_type="RETRIEVAL_QUERY",
                add_prefix=True,
            )
            logger.debug("embeddings_generated", num_embeddings=len(embeddings))

            # Step 3: Classify using k-NN
            classification = self._classify_with_knn(embeddings)

            # Step 4: Create DecisionAnalysis result
            result = DecisionAnalysis(
                intimation_id=intimation_id or 0,
                decision_type="RAG_CLASSIFIED",
                outcome=classification["outcome"],
                winner_lawyer_oab=None,
                loser_lawyer_oab=None,
                plaintiff_won=classification["outcome"]
                in ["WIN", "PARTIAL"],
                confidence_score=classification["confidence"],
                summary=f"RAG classification with {classification['confidence']:.2%} confidence. "
                f"Votes: {classification['votes']}",
                analysis_method="rag",
                rag_confidence=classification["confidence"],
                rag_votes=classification["votes"],
            )

            logger.info(
                "rag_analysis_complete",
                intimation_id=intimation_id,
                outcome=result.outcome,
                confidence=result.confidence_score,
            )

            return result

        except Exception as e:
            logger.error(
                "rag_analysis_failed",
                intimation_id=intimation_id,
                error=str(e),
            )
            raise

    def _classify_with_knn(
        self,
        embeddings: list[list[float]],
    ) -> dict[str, Any]:
        """Classify decision using k-NN voting across all chunk embeddings.

        Args:
            embeddings: List of embedding vectors for the decision chunks.

        Returns:
            Dictionary with classification results:
                - outcome: The predicted outcome (WIN/LOSS/PARTIAL/UNKNOWN)
                - confidence: Confidence score (0.0-1.0)
                - votes: Dictionary of vote counts per outcome
                - total_neighbors: Total number of neighbors considered
        """
        all_neighbors = []

        # For each chunk embedding, find k nearest neighbors
        for embedding in embeddings:
            neighbors = self.vector_store.search(
                table_name=self.ground_truth_table,
                query_vector=embedding,
                k=self.k_neighbors,
                columns=["outcome"],
            )

            # Collect the outcomes from neighbors
            outcomes = [n["outcome"] for n in neighbors]
            all_neighbors.extend(outcomes)

        # Vote by majority
        vote_counter = Counter(all_neighbors)
        most_common = vote_counter.most_common(1)[0]
        winner_outcome = most_common[0]
        winner_votes = most_common[1]

        # Calculate confidence as percentage of votes for winner
        total_votes = len(all_neighbors)
        confidence = winner_votes / total_votes if total_votes > 0 else 0.0

        result = {
            "outcome": winner_outcome,
            "confidence": confidence,
            "votes": dict(vote_counter),
            "total_neighbors": total_votes,
        }

        logger.debug(
            "knn_classification",
            outcome=winner_outcome,
            confidence=confidence,
            votes=result["votes"],
        )

        return result

    async def analyze_batch(
        self,
        texts: list[str],
        intimation_ids: list[int] | None = None,
    ) -> list[DecisionAnalysis]:
        """Analyze multiple decision texts.

        Args:
            texts: List of decision texts.
            intimation_ids: Optional list of intimation IDs (same length as texts).

        Returns:
            List of DecisionAnalysis results.
        """
        if intimation_ids is None:
            intimation_ids = [None] * len(texts)

        logger.info("rag_batch_analysis_start", total=len(texts))

        results = []
        for text, int_id in zip(texts, intimation_ids, strict=False):
            try:
                result = await self.analyze_text(text, int_id)
                results.append(result)
            except Exception as e:
                logger.error(
                    "batch_analysis_item_failed",
                    intimation_id=int_id,
                    error=str(e),
                )
                # Create a low-confidence UNKNOWN result
                results.append(
                    DecisionAnalysis(
                        intimation_id=int_id or 0,
                        decision_type="RAG_FAILED",
                        outcome="UNKNOWN",
                        winner_lawyer_oab=None,
                        loser_lawyer_oab=None,
                        plaintiff_won=False,
                        confidence_score=0.0,
                        summary=f"RAG analysis failed: {str(e)}",
                        analysis_method="rag",
                        rag_confidence=0.0,
                        rag_votes={},
                    )
                )

        successful = sum(1 for r in results if r.confidence_score > 0)
        logger.info(
            "rag_batch_analysis_complete",
            total=len(texts),
            successful=successful,
            failed=len(texts) - successful,
        )

        return results

    @staticmethod
    def calculate_cost(num_decisions: int) -> float:
        """Calculate the cost of analyzing decisions with RAG.

        Args:
            num_decisions: Number of decisions to analyze.

        Returns:
            Estimated cost in USD.
        """
        return num_decisions * COST_PER_DECISION
