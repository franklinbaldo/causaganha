"""Module for generating embeddings using the Gemini embedding model."""

import os
import google.generativeai as genai
import structlog
from typing import List

logger = structlog.get_logger()

class GeminiEmbedder:
    """
    Generates embeddings for text using the specified Gemini embedding model.
    Assumes GEMINI_API_KEY is set in environment variables.
    """

    def __init__(self, model_name: str = "gemini-embedding-001"):
        self.model_name = model_name
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        genai.configure(api_key=api_key)
        self.model = genai.get_model(self.model_name)
        logger.info("gemini_embedder_initialized", model=self.model_name)

    async def embed_text(self, text: str) -> List[float]:
        """
        Generates an embedding for a single piece of text.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        try:
            response = await self.model.embed_content(
                model=self.model_name,
                content=text
            )
            # The embedding is usually in response['embedding'] or response.embedding
            # Need to check the exact structure of the response from the API
            # For now, assuming response.embedding as per typical genai client
            return response.embedding
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a batch of texts.

        Args:
            texts: A list of texts to embed.

        Returns:
            A list of embedding vectors, each a list of floats.
        """
        if not texts:
            return []

        embeddings = []
        try:
            # The genai.get_model().embed_content might not support batch directly
            # Or it might require a specific batching mechanism.
            # For simplicity, doing it sequentially for now.
            # This can be optimized later if the API supports true batching.
            for text in texts:
                embedding = await self.embed_text(text)
                embeddings.append(embedding)
            return embeddings
        except Exception as e:
            logger.error("batch_embedding_generation_failed", error=str(e))
            raise
