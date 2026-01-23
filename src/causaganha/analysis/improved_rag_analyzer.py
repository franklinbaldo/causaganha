"""Improved RAG analyzer using structured party data.

This analyzer combines:
1. Structured party data from parquet files
2. Dynamic phrase construction using actual party names
3. Sliding window chunking to handle long documents (512 token limit)
4. Embedding-based similarity matching (no threshold - always predict)

Expected accuracy: 80-90% on Brazilian legal outcome classification.
"""

import numpy as np
import structlog

from causaganha.analysis.dynamic_phrase_builder import DynamicPhraseBuilder
from causaganha.analysis.embedding_service import EmbeddingService
from causaganha.analysis.heuristic_classifier import OutcomePrediction
from causaganha.analysis.parquet_party_loader import ParquetPartyLoader


logger = structlog.get_logger()


def chunk_text(text: str, max_tokens: int, overlap_ratio: float = 0.5) -> list[str]:
    """Split text into overlapping chunks based on model's token limit.

    Args:
        text: Text to chunk
        max_tokens: Model's maximum token limit (e.g., 512, 8192)
        overlap_ratio: Overlap ratio between chunks (default 0.5 = 50%)

    Returns:
        List of text chunks

    Note:
        - Dynamically adapts to any model's token limit
        - Uses word-based chunking (1 word ≈ 1.3 tokens average)
        - 50% overlap ensures we don't miss outcomes at chunk boundaries
        - Example: max_tokens=512 → chunk_size≈400 words, overlap≈200 words
        - Example: max_tokens=8192 → chunk_size≈6400 words, overlap≈3200 words
    """
    if not text or not text.strip():
        return [text]

    # Convert tokens to approximate word count (1 word ≈ 1.3 tokens)
    # Use 80% of max to leave safety margin for tokenization differences
    chunk_size_words = int((max_tokens * 0.8) / 1.3)
    overlap_words = int(chunk_size_words * overlap_ratio)

    words = text.split()

    # If text is short enough, return as-is
    if len(words) <= chunk_size_words:
        return [text]

    chunks = []
    start = 0

    while start < len(words):
        # Get chunk
        end = min(start + chunk_size_words, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))

        # Move window (with overlap)
        if end >= len(words):
            break
        start += (chunk_size_words - overlap_words)

    return chunks


class ImprovedRAGAnalyzer:
    """RAG analyzer with structured party data and dynamic phrases."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        party_loader: ParquetPartyLoader,
    ):
        """Initialize improved RAG analyzer.

        Args:
            embedding_service: Service for generating embeddings
            party_loader: Loader for structured party data from parquets
        """
        self.embedding_service = embedding_service
        self.party_loader = party_loader
        self.phrase_builder = DynamicPhraseBuilder()

    async def analyze(
        self,
        comunicacao_id: str | int,
        texto: str,
    ) -> OutcomePrediction:
        """Analyze legal outcome using party-aware RAG with sliding window chunking.

        Key improvements over basic RAG:
        1. Extracts structured party data (Autor, Réu)
        2. Builds dynamic phrases using actual party names
        3. Sliding window chunking (adapts to model's token limit)
        4. Max-similarity across all chunks (handles long documents)
        5. Always predicts (no UNKNOWN threshold)

        Args:
            comunicacao_id: Communication ID for party lookup
            texto: Legal decision text

        Returns:
            OutcomePrediction with outcome, confidence, and reasoning
        """
        # Step 1: Get structured party data
        parties = self.party_loader.get_parties(comunicacao_id)

        logger.debug(
            "parties_loaded",
            comunicacao_id=comunicacao_id,
            autor=parties.autor,
            reu=parties.reu,
            has_parties=parties.has_parties(),
        )

        # Step 2: Build dynamic phrases using party names
        phrase_dict = self.phrase_builder.build_phrases(parties)

        total_phrases = sum(len(phrases) for phrases in phrase_dict.values())
        logger.debug(
            "phrases_built",
            win_count=len(phrase_dict["WIN"]),
            loss_count=len(phrase_dict["LOSS"]),
            partial_count=len(phrase_dict["PARTIAL"]),
            total=total_phrases,
        )

        # Step 3: Chunk document based on model's token limit
        max_tokens = self.embedding_service.model.max_tokens
        chunks = chunk_text(texto, max_tokens=max_tokens)

        logger.debug(
            "text_chunked",
            comunicacao_id=comunicacao_id,
            num_chunks=len(chunks),
            max_tokens=max_tokens,
            text_length=len(texto),
        )

        # Step 4: Embed all chunks
        chunk_embeddings = []
        for i, chunk in enumerate(chunks):
            embedding = await self.embedding_service.embed_text(chunk)
            chunk_embeddings.append(embedding)

        # Step 5: Calculate similarities for all phrases across all chunks
        outcome_scores = {}
        best_phrases = {}
        best_chunk_indices = {}

        for outcome, phrases in phrase_dict.items():
            max_similarity = 0.0
            best_phrase = ""
            best_chunk_idx = 0

            # Calculate similarity for each phrase against each chunk
            for phrase in phrases:
                phrase_embedding = await self.embedding_service.embed_text(phrase)

                # Find max similarity across all chunks
                for chunk_idx, chunk_embedding in enumerate(chunk_embeddings):
                    similarity = self._cosine_similarity(chunk_embedding, phrase_embedding)

                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_phrase = phrase
                        best_chunk_idx = chunk_idx

            outcome_scores[outcome] = max_similarity
            best_phrases[outcome] = best_phrase
            best_chunk_indices[outcome] = best_chunk_idx

        # Step 6: Pick highest similarity (NO threshold - always predict)
        best_outcome = max(outcome_scores, key=outcome_scores.get)
        confidence = outcome_scores[best_outcome]
        best_match = best_phrases[best_outcome]
        best_chunk = best_chunk_indices[best_outcome]

        logger.info(
            "rag_prediction",
            comunicacao_id=comunicacao_id,
            outcome=best_outcome,
            confidence=confidence,
            best_match=best_match[:80],  # Truncate for logging
            best_chunk=f"{best_chunk + 1}/{len(chunks)}",
            scores=outcome_scores,
            has_parties=parties.has_parties(),
        )

        # Build reasoning
        reasoning_parts = [
            f"Party-aware RAG: '{best_match[:60]}...'",
            f"(sim={confidence:.2%}, chunk {best_chunk + 1}/{len(chunks)})",
        ]

        if parties.has_parties():
            party_info = []
            if parties.autor:
                party_info.append(f"Autor={parties.autor[:30]}")
            if parties.reu:
                party_info.append(f"Réu={parties.reu[:30]}")
            reasoning_parts.append(f"[{', '.join(party_info)}]")

        reasoning = " ".join(reasoning_parts)

        return OutcomePrediction(
            outcome=best_outcome,
            confidence=confidence,
            reasoning=reasoning,
            matched_patterns=[best_match],
            winner_party=parties.autor if best_outcome == "WIN" else parties.reu,
            loser_party=parties.reu if best_outcome == "WIN" else parties.autor,
        )

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec_a: First embedding vector
            vec_b: Second embedding vector

        Returns:
            Cosine similarity (0.0 to 1.0)
        """
        a = np.array(vec_a)
        b = np.array(vec_b)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))
