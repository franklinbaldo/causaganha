"""Zero-shot RAG analyzer using cosine similarity with generic outcome phrases."""

from collections import Counter
from typing import Any

import numpy as np
import structlog

from causaganha.v2.analysis.embedding_service import EmbeddingService
from causaganha.v2.analysis.models import DecisionAnalysis


logger = structlog.get_logger()

# Generic phrases representing each outcome
# These are embedded once and reused for all decisions
OUTCOME_PHRASES = {
    "WIN": [
        "julgo procedente o pedido do autor",
        "condeno o réu ao pagamento",
        "defiro o pedido do requerente",
        "procedente a ação",
    ],
    "LOSS": [
        "julgo improcedente o pedido",
        "condeno o autor ao pagamento",
        "indefiro o pedido",
        "improcedente a ação",
        "nego provimento",
    ],
    "PARTIAL": [
        "julgo parcialmente procedente",
        "parcialmente procedente o pedido",
        "defiro em parte",
        "procedência parcial",
    ],
    "UNKNOWN": [
        "despacho processual",
        "intimação para manifestação",
        "aguarde-se",
        "certidão de publicação",
    ],
}

# Cost per decision using embeddings API
COST_PER_DECISION = 0.000004  # Approximate for embedding-only approach


class RAGAnalyzer:
    """Zero-shot decision analyzer using cosine similarity with generic phrases."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        """Initialize the RAG analyzer.

        Args:
            embedding_service: Initialized EmbeddingService.
        """
        self.embedding_service = embedding_service
        self.outcome_embeddings: dict[str, list[list[float]]] = {}
        self._embeddings_initialized = False

        logger.info("rag_analyzer_initialized", mode="zero_shot_similarity")

    @classmethod
    async def create(cls, api_key: str | None = None) -> "RAGAnalyzer":
        """Factory method to create RAGAnalyzer with default embedding service.

        Args:
            api_key: API key for embedding service (optional).

        Returns:
            Initialized RAGAnalyzer.
        """
        # Create embedding service (auto-select provider)
        embedding_service = await EmbeddingService.create(api_key=api_key)
        return cls(embedding_service)

    async def _initialize_outcome_embeddings(self) -> None:
        """Embed all generic outcome phrases once (cached for reuse)."""
        if self._embeddings_initialized:
            return

        logger.info("initializing_outcome_phrase_embeddings")

        for outcome, phrases in OUTCOME_PHRASES.items():
            # Embed all phrases for this outcome
            embeddings = await self.embedding_service.embed_batch(
                phrases,
                task_type="RETRIEVAL_DOCUMENT",
                add_prefix=False,  # Phrases are already outcome-specific
            )
            self.outcome_embeddings[outcome] = embeddings

            logger.debug(
                "outcome_phrases_embedded",
                outcome=outcome,
                num_phrases=len(phrases),
            )

        self._embeddings_initialized = True
        logger.info("outcome_embeddings_ready", total_outcomes=len(self.outcome_embeddings))

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First embedding vector.
            vec2: Second embedding vector.

        Returns:
            Cosine similarity score (0.0 to 1.0).
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _classify_chunk(self, chunk_embedding: list[float]) -> dict[str, Any]:
        """Classify a single chunk by comparing with outcome phrases.

        Args:
            chunk_embedding: Embedding vector of the decision chunk.

        Returns:
            Dictionary with outcome and similarity scores.
        """
        similarities = {}

        for outcome, phrase_embeddings in self.outcome_embeddings.items():
            # Calculate similarity with each phrase for this outcome
            outcome_similarities = [
                self._cosine_similarity(chunk_embedding, phrase_emb)
                for phrase_emb in phrase_embeddings
            ]
            # Use max similarity across all phrases for this outcome
            similarities[outcome] = max(outcome_similarities)

        # Find outcome with highest similarity
        best_outcome = max(similarities, key=similarities.get)
        best_score = similarities[best_outcome]

        return {
            "outcome": best_outcome,
            "score": best_score,
            "all_scores": similarities,
        }

    async def analyze_text(
        self,
        text: str,
        intimation_id: int | None = None,
    ) -> DecisionAnalysis:
        """Analyze decision text using zero-shot similarity.

        Args:
            text: The decision text to analyze.
            intimation_id: Optional intimation ID for logging.

        Returns:
            DecisionAnalysis with classification result.
        """
        # Initialize outcome embeddings if not done yet
        await self._initialize_outcome_embeddings()

        logger.info(
            "rag_analysis_start",
            intimation_id=intimation_id,
            text_length=len(text),
        )

        try:
            # Step 1: Chunk the text
            chunks = self.embedding_service.chunk_text(text)
            logger.debug("text_chunked", num_chunks=len(chunks))

            if not chunks:
                # Empty text - return UNKNOWN
                return DecisionAnalysis(
                    intimation_id=intimation_id or 0,
                    decision_type="UNKNOWN",
                    outcome="UNKNOWN",
                    plaintiff_won=False,
                    confidence_score=0.0,
                    summary="Empty text - classified as UNKNOWN",
                    analysis_method="rag",
                )

            # Step 2: Embed all chunks
            chunk_embeddings = await self.embedding_service.embed_batch(
                chunks,
                task_type="RETRIEVAL_QUERY",
                add_prefix=True,
            )
            logger.debug("chunks_embedded", num_embeddings=len(chunk_embeddings))

            # Step 3: Classify each chunk
            chunk_classifications = []
            for chunk_emb in chunk_embeddings:
                classification = self._classify_chunk(chunk_emb)
                chunk_classifications.append(classification)

            # Step 4: Aggregate across chunks (majority vote)
            outcomes = [c["outcome"] for c in chunk_classifications]
            outcome_counts = Counter(outcomes)
            final_outcome = outcome_counts.most_common(1)[0][0]

            # Calculate confidence (proportion of chunks agreeing)
            total_chunks = len(chunks)
            agreeing_chunks = outcome_counts[final_outcome]
            confidence = agreeing_chunks / total_chunks if total_chunks > 0 else 0.0

            # Average similarity scores for the winning outcome
            avg_score = np.mean(
                [c["score"] for c in chunk_classifications if c["outcome"] == final_outcome]
            )

            # Combine vote confidence and similarity score
            combined_confidence = (confidence + avg_score) / 2

            # Create result
            result = DecisionAnalysis(
                intimation_id=intimation_id or 0,
                decision_type="RAG_CLASSIFIED",
                outcome=final_outcome,
                plaintiff_won=final_outcome in ["WIN", "PARTIAL"],
                confidence_score=combined_confidence,
                summary=f"Zero-shot RAG: {final_outcome} ({agreeing_chunks}/{total_chunks} chunks, "
                f"avg similarity: {avg_score:.3f})",
                analysis_method="rag",
                rag_confidence=combined_confidence,
                rag_votes=dict(outcome_counts),
            )

            logger.info(
                "rag_analysis_complete",
                intimation_id=intimation_id,
                outcome=result.outcome,
                confidence=result.confidence_score,
                vote_distribution=dict(outcome_counts),
            )

            return result

        except Exception as e:
            logger.exception(
                "rag_analysis_failed",
                intimation_id=intimation_id,
                error=str(e),
            )
            raise

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

        # Initialize outcome embeddings once for all
        await self._initialize_outcome_embeddings()

        logger.info("rag_batch_analysis_start", total=len(texts))

        results = []
        for text, int_id in zip(texts, intimation_ids, strict=False):
            try:
                result = await self.analyze_text(text, int_id)
                results.append(result)
            except Exception as e:
                logger.exception(
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
                        plaintiff_won=False,
                        confidence_score=0.0,
                        summary=f"RAG analysis failed: {e!s}",
                        analysis_method="rag",
                        rag_confidence=0.0,
                        rag_votes={},
                    ),
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
    def calculate_cost(num_decisions: int, avg_chunks_per_decision: int = 5) -> float:
        """Calculate the cost of analyzing decisions with zero-shot RAG.

        Args:
            num_decisions: Number of decisions to analyze.
            avg_chunks_per_decision: Average chunks per decision.

        Returns:
            Estimated cost in USD.
        """
        # Cost includes:
        # - One-time: embed outcome phrases (4 outcomes × ~4 phrases = 16 embeddings)
        # - Per decision: embed chunks (~5 chunks per decision)
        return num_decisions * COST_PER_DECISION
