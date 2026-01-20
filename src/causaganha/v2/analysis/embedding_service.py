"""Embedding service for generating text embeddings using Google's text-embedding-004 model."""

import asyncio
import os
from typing import Literal

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

# Embedding configuration
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 768
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
CONTEXTUAL_PREFIX = """Analise esta parte da decisão judicial para classificar o resultado (WIN/LOSS/PARTIAL/UNKNOWN).
Considere: vitória do autor, vitória do réu, parcial, ou resultado não claro."""


TaskType = Literal["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"]


class EmbeddingService:
    """Service for generating text embeddings with Google's API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = EMBEDDING_MODEL,
        max_retries: int = 3,
    ) -> None:
        """Initialize the embedding service.

        Args:
            api_key: Google API key. If None, reads from GOOGLE_API_KEY env var.
            model: Embedding model to use (default: text-embedding-004).
            max_retries: Maximum number of retry attempts for failed requests.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key must be provided or set in GOOGLE_API_KEY env var"
            )

        self.model = model
        self.max_retries = max_retries
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

        logger.info(
            "embedding_service_initialized",
            model=model,
            max_retries=max_retries,
        )

    def _add_contextual_prefix(self, text: str) -> str:
        """Add contextual prefix to improve embedding quality.

        Args:
            text: Original text.

        Returns:
            Text with contextual prefix prepended.
        """
        return f"{CONTEXTUAL_PREFIX}\n\n{text}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def embed_text(
        self,
        text: str,
        task_type: TaskType = "RETRIEVAL_QUERY",
        add_prefix: bool = True,
    ) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.
            task_type: Type of task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT).
            add_prefix: Whether to add contextual prefix.

        Returns:
            Embedding vector (768 dimensions).

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        if add_prefix:
            text = self._add_contextual_prefix(text)

        url = f"{self.base_url}/models/{self.model}:embedContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        payload = {
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()

                data = response.json()
                embedding = data["embedding"]["values"]

                logger.debug(
                    "embedding_generated",
                    text_length=len(text),
                    embedding_dim=len(embedding),
                    task_type=task_type,
                )

                return embedding

            except httpx.HTTPError as e:
                logger.error(
                    "embedding_generation_failed",
                    error=str(e),
                    text_length=len(text),
                )
                raise

    async def embed_batch(
        self,
        texts: list[str],
        task_type: TaskType = "RETRIEVAL_QUERY",
        add_prefix: bool = True,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts concurrently.

        Args:
            texts: List of texts to embed.
            task_type: Type of task for all texts.
            add_prefix: Whether to add contextual prefix to all texts.

        Returns:
            List of embedding vectors.
        """
        logger.info("embedding_batch_start", count=len(texts))

        tasks = [
            self.embed_text(text, task_type=task_type, add_prefix=add_prefix)
            for text in texts
        ]

        embeddings = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        successful = []
        failed = 0
        for emb in embeddings:
            if isinstance(emb, Exception):
                logger.error("embedding_failed_in_batch", error=str(emb))
                failed += 1
                successful.append([0.0] * EMBEDDING_DIMENSION)  # Zero vector fallback
            else:
                successful.append(emb)

        logger.info(
            "embedding_batch_complete",
            total=len(texts),
            successful=len(texts) - failed,
            failed=failed,
        )

        return successful

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
    ) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk.
            chunk_size: Size of each chunk in characters.
            overlap: Number of characters to overlap between chunks.

        Returns:
            List of text chunks.
        """
        if not text:
            return []

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Don't create tiny final chunks
            if end >= len(text):
                chunks.append(chunk)
                break

            chunks.append(chunk)
            start = end - overlap  # Step back by overlap amount

        logger.debug(
            "text_chunked",
            original_length=len(text),
            num_chunks=len(chunks),
            chunk_size=chunk_size,
            overlap=overlap,
        )

        return chunks

    async def embed_chunked_text(
        self,
        text: str,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
        task_type: TaskType = "RETRIEVAL_QUERY",
    ) -> list[list[float]]:
        """Chunk text and generate embeddings for all chunks.

        Args:
            text: Text to process.
            chunk_size: Size of each chunk.
            overlap: Overlap between chunks.
            task_type: Task type for embeddings.

        Returns:
            List of embedding vectors for each chunk.
        """
        chunks = self.chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        return await self.embed_batch(chunks, task_type=task_type, add_prefix=True)
