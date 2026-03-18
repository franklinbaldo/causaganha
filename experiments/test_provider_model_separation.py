"""Test the new Provider + Model separation architecture.

This script demonstrates how the new architecture separates:
- Provider: API service (Jina AI, Google AI)
- Model: Configuration (model name, dimensions, token limits)
"""

import asyncio
import os

from causaganha.analysis.embedding_models import (
    GOOGLE_GEMINI_768,
    JINA_V3_1024,
    JINA_V4_768,
    JINA_V4_1024,
    list_models,
)
from causaganha.analysis.embedding_service_v2 import EmbeddingService
from causaganha.analysis.providers import JinaProvider


async def test_provider_model_separation() -> None:
    """Test that Provider and Model are properly separated."""
    # List all available models
    all_models = list_models()
    for _model in all_models:
        pass

    # Test 1: One provider, multiple models

    if os.getenv("JINA_API_KEY"):
        # Create ONE provider instance
        jina_provider = JinaProvider()

        # Use the SAME provider with DIFFERENT models
        test_text = "This is a test sentence for embedding."

        # Model 1: Jina v4 with 1024 dimensions
        await jina_provider.embed_text(test_text, model=JINA_V4_1024)

        # Model 2: Jina v4 with 768 dimensions (different dimension, same provider!)
        await jina_provider.embed_text(test_text, model=JINA_V4_768)

        # Model 3: Jina v3 with 1024 dimensions (different model version!)
        await jina_provider.embed_text(test_text, model=JINA_V3_1024)

    # Test 2: EmbeddingService with explicit model selection
    if os.getenv("JINA_API_KEY"):
        # Create service with specific model
        service_v4 = await EmbeddingService.create(
            provider="jina",
            model=JINA_V4_1024,  # Explicit model
        )

        # Embed a text
        await service_v4.embed_text("Legal decision text example")

    # Test 3: Auto-selection with default models
    # Auto-select (will pick Jina if available, Google otherwise)
    await EmbeddingService.create(provider="auto")

    # Test 4: Model validation (provider mismatch)
    if os.getenv("JINA_API_KEY"):
        jina_provider = JinaProvider()

        # Try to use a Google model with Jina provider (should fail with ValueError)
        await jina_provider.embed_text("test", model=GOOGLE_GEMINI_768)

    # Summary


if __name__ == "__main__":
    asyncio.run(test_provider_model_separation())
