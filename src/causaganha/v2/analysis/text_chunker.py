"""Dynamic text chunking utilities for embedding providers.

This module provides intelligent text chunking that adapts to the maximum
token limit of the embedding model being used.
"""

import re
from typing import Protocol

import structlog

logger = structlog.get_logger()


class TokenCounter(Protocol):
    """Protocol for token counting."""

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        ...


class SimpleTokenCounter:
    """Simple token counter using character-based estimation.

    Estimates ~4 characters per token for English/Portuguese text.
    """

    def count_tokens(self, text: str) -> int:
        """Estimate token count from character length.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimate: 4 characters per token
        return len(text) // 4


class TextChunker:
    """Dynamic text chunker that adapts to embedding model token limits."""

    # Legal decision section markers (Brazilian Portuguese)
    SECTION_MARKERS = [
        r"ACÓRDÃO",
        r"SENTENÇA",
        r"DECISÃO",
        r"FUNDAMENTAÇÃO",
        r"DISPOSITIVO",
        r"RELATÓRIO",
        r"VOTO",
        r"EMENTA",
    ]

    def __init__(
        self,
        max_tokens: int,
        overlap_tokens: int = 128,
        token_counter: TokenCounter | None = None,
    ):
        """Initialize text chunker.

        Args:
            max_tokens: Maximum tokens per chunk (from embedding provider)
            overlap_tokens: Number of overlapping tokens between chunks
            token_counter: Token counter implementation (defaults to SimpleTokenCounter)
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.token_counter = token_counter or SimpleTokenCounter()

        # Reserve 5% for safety margin
        self.safe_max_tokens = int(max_tokens * 0.95)

        logger.info(
            "text_chunker_initialized",
            max_tokens=max_tokens,
            safe_max_tokens=self.safe_max_tokens,
            overlap_tokens=overlap_tokens,
        )

    def needs_chunking(self, text: str) -> bool:
        """Check if text needs to be chunked.

        Args:
            text: Input text

        Returns:
            True if text exceeds safe token limit
        """
        token_count = self.token_counter.count_tokens(text)
        return token_count > self.safe_max_tokens

    def chunk_by_sections(self, text: str) -> list[str]:
        """Chunk text by legal document sections.

        Attempts to split on section markers (ACÓRDÃO, SENTENÇA, etc.)
        to preserve semantic meaning.

        Args:
            text: Full legal decision text

        Returns:
            List of text chunks
        """
        # Build regex pattern for all section markers
        pattern = r"(?=" + "|".join(self.SECTION_MARKERS) + r")"

        # Split on section markers (keep the markers)
        sections = re.split(pattern, text)
        sections = [s.strip() for s in sections if s.strip()]

        if not sections:
            # Fallback to sliding window if no sections found
            return self.chunk_by_sliding_window(text)

        # Combine sections into chunks that fit within token limit
        chunks = []
        current_chunk = ""

        for section in sections:
            # Check if adding this section would exceed limit
            combined = current_chunk + "\n\n" + section if current_chunk else section
            combined_tokens = self.token_counter.count_tokens(combined)

            if combined_tokens <= self.safe_max_tokens:
                # Add to current chunk
                current_chunk = combined
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk)

                # Check if section itself is too large
                section_tokens = self.token_counter.count_tokens(section)
                if section_tokens > self.safe_max_tokens:
                    # Section is too large, split it with sliding window
                    section_chunks = self.chunk_by_sliding_window(section)
                    chunks.extend(section_chunks)
                    current_chunk = ""
                else:
                    current_chunk = section

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        logger.info(
            "chunked_by_sections",
            num_chunks=len(chunks),
            original_tokens=self.token_counter.count_tokens(text),
        )

        return chunks

    def chunk_by_sliding_window(self, text: str) -> list[str]:
        """Chunk text using sliding window with overlap.

        Args:
            text: Input text

        Returns:
            List of overlapping text chunks
        """
        # Convert to character-based chunks (approximate)
        chars_per_token = 4
        max_chars = self.safe_max_tokens * chars_per_token
        overlap_chars = self.overlap_tokens * chars_per_token

        chunks = []
        start = 0

        while start < len(text):
            end = start + max_chars

            # Don't go past end of text
            if end >= len(text):
                chunks.append(text[start:])
                break

            # Try to break at sentence boundary
            chunk_text = text[start:end]

            # Look for sentence endings near the end
            sentence_end = max(
                chunk_text.rfind(". "),
                chunk_text.rfind(".\n"),
                chunk_text.rfind("! "),
                chunk_text.rfind("? "),
            )

            if sentence_end > max_chars * 0.8:  # At least 80% of max size
                end = start + sentence_end + 1

            chunks.append(text[start:end])

            # Move start forward with overlap
            start = end - overlap_chars

        logger.info(
            "chunked_by_sliding_window",
            num_chunks=len(chunks),
            original_tokens=self.token_counter.count_tokens(text),
        )

        return chunks

    def chunk_text(self, text: str, strategy: str = "auto") -> list[str]:
        """Chunk text adaptively based on content and token limit.

        Args:
            text: Input text
            strategy: Chunking strategy ('auto', 'sections', 'sliding_window')

        Returns:
            List of text chunks that fit within token limit
        """
        # Check if chunking is needed
        if not self.needs_chunking(text):
            return [text]

        logger.info(
            "text_requires_chunking",
            text_length=len(text),
            estimated_tokens=self.token_counter.count_tokens(text),
            max_tokens=self.max_tokens,
        )

        # Auto-detect best strategy
        if strategy == "auto":
            # Check if text contains legal section markers
            has_sections = any(
                re.search(marker, text) for marker in self.SECTION_MARKERS
            )
            strategy = "sections" if has_sections else "sliding_window"

        # Chunk with selected strategy
        if strategy == "sections":
            return self.chunk_by_sections(text)
        else:
            return self.chunk_by_sliding_window(text)


def create_chunker_for_provider(provider) -> TextChunker:
    """Create a TextChunker configured for the given embedding provider.

    Args:
        provider: EmbeddingProvider instance with max_token_limit property

    Returns:
        TextChunker configured with provider's token limit
    """
    max_tokens = provider.max_token_limit

    logger.info(
        "creating_chunker_for_provider",
        provider=type(provider).__name__,
        max_tokens=max_tokens,
    )

    # Use 128 token overlap for good context preservation
    return TextChunker(max_tokens=max_tokens, overlap_tokens=128)
