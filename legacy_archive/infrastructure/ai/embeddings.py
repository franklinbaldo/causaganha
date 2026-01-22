"""Embedding-based decision analysis using Gemini."""

import os
from typing import Any

import google.generativeai as genai
import numpy as np
import structlog


logger = structlog.get_logger()


class EmbeddingAnalyzer:
    """Analyze decisions using embeddings and semantic similarity."""

    def __init__(self, api_key: str | None = None):
        """Initialize the embedding analyzer.

        Args:
            api_key: Optional Gemini API key. Falls back to env vars.
        """
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY required")

        genai.configure(api_key=key)
        # Updated to current model (text-embedding-004 was deprecated August 2025)
        self.model_name = "models/gemini-embedding-001"

        # Reference phrases for outcome classification
        self.reference_phrases = {
            "WIN_AUTOR": [
                "a parte autora venceu",
                "procedente o pedido do autor",
                "julgo procedente a ação",
                "dou provimento ao recurso do autor",
                "condeno o réu a pagar",
                "defiro o pedido do requerente",
                "acolho o pedido da parte autora",
                "favorável ao autor",
                "vencedor: autor",
            ],
            "LOSS_AUTOR": [
                "a parte autora perdeu",
                "improcedente o pedido",
                "julgo improcedente a ação",
                "nego provimento ao recurso do autor",
                "condeno o autor em custas",
                "indefiro o pedido do autor",
                "rejeito o pedido da parte autora",
                "favorável ao réu",
                "vencedor: réu",
            ],
            "PARTIAL": [
                "parcialmente procedente",
                "procedente em parte",
                "acolho parcialmente",
                "defiro em parte",
                "acordo homologado",
                "conciliação",
            ],
            "UNKNOWN": [
                "intimo as partes",
                "determino a citação",
                "abro vista",
                "manifeste-se",
                "apresente documentos",
                "aguarde-se",
            ],
        }

        # Pre-compute reference embeddings
        self.reference_embeddings: dict[str, list[np.ndarray]] = {}
        logger.info("precomputing_reference_embeddings")
        for outcome, phrases in self.reference_phrases.items():
            self.reference_embeddings[outcome] = [self._get_embedding(phrase) for phrase in phrases]
        logger.info("reference_embeddings_ready", count=len(self.reference_embeddings))

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        result = genai.embed_content(
            model=self.model_name,
            content=text,
            task_type="retrieval_document",
        )
        return np.array(result["embedding"])

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
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
                if last_period > chunk_size * 0.7:  # Only if period is in last 30%
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    def analyze_decision_outcome(
        self,
        text: str,
        chunk_size: int = 500,
        top_k: int = 3,
    ) -> dict[str, Any]:
        """Analyze decision outcome using embedding similarity.

        Args:
            text: Decision text to analyze
            chunk_size: Size of chunks for embedding
            top_k: Number of top similar reference phrases to consider

        Returns:
            Analysis result with outcome and confidence
        """
        logger.info("analyzing_decision_with_embeddings", text_length=len(text))

        # Chunk the decision text
        chunks = self.chunk_text(text, chunk_size=chunk_size)
        logger.info("text_chunked", num_chunks=len(chunks))

        # Get embeddings for all chunks
        chunk_embeddings = [self._get_embedding(chunk) for chunk in chunks]

        # Calculate similarity scores for each outcome
        outcome_scores: dict[str, list[float]] = {
            outcome: [] for outcome in self.reference_phrases.keys()
        }

        for chunk_emb in chunk_embeddings:
            for outcome, ref_embeddings in self.reference_embeddings.items():
                # Calculate similarity with all reference phrases for this outcome
                similarities = [
                    self._cosine_similarity(chunk_emb, ref_emb) for ref_emb in ref_embeddings
                ]
                # Take max similarity for this chunk
                max_sim = max(similarities) if similarities else 0.0
                outcome_scores[outcome].append(max_sim)

        # Aggregate scores across chunks (take max score across all chunks)
        final_scores = {
            outcome: max(scores) if scores else 0.0 for outcome, scores in outcome_scores.items()
        }

        # Find best matching outcome
        best_outcome = max(final_scores, key=final_scores.get)  # type: ignore
        confidence = final_scores[best_outcome]

        # Convert outcome to standard format
        if best_outcome == "WIN_AUTOR":
            outcome_label = "WIN"
        elif best_outcome == "LOSS_AUTOR":
            outcome_label = "LOSS"
        elif best_outcome == "PARTIAL":
            outcome_label = "PARTIAL"
        else:
            outcome_label = "UNKNOWN"

        logger.info(
            "embedding_analysis_complete",
            outcome=outcome_label,
            confidence=confidence,
            all_scores=final_scores,
        )

        return {
            "outcome": outcome_label,
            "confidence": confidence,
            "all_scores": final_scores,
            "num_chunks": len(chunks),
            "method": "embedding_similarity",
        }

    def batch_analyze(self, texts: list[str], chunk_size: int = 500) -> list[dict[str, Any]]:
        """Analyze multiple decisions in batch.

        Args:
            texts: List of decision texts
            chunk_size: Size of chunks for embedding

        Returns:
            List of analysis results
        """
        results = []
        for i, text in enumerate(texts):
            logger.info("batch_processing", index=i, total=len(texts))
            result = self.analyze_decision_outcome(text, chunk_size=chunk_size)
            results.append(result)

        return results
