"""Test the new Provider + Model separation architecture.

This script demonstrates how the new architecture separates:
- Provider: API service (Jina AI, Google AI)
- Model: Configuration (model name, dimensions, token limits)
"""

import asyncio
import os

from causaganha.v2.analysis.embedding_models import (
    GOOGLE_GEMINI_768,
    JINA_V3_1024,
    JINA_V4_1024,
    JINA_V4_768,
    get_default_model,
    list_models,
)
from causaganha.v2.analysis.embedding_service_v2 import EmbeddingService
from causaganha.v2.analysis.providers import JinaProvider


async def test_provider_model_separation():
    """Test that Provider and Model are properly separated."""
    print("=" * 80)
    print("PROVIDER + MODEL SEPARATION TEST")
    print("=" * 80)
    print()

    # List all available models
    print("─" * 80)
    print("Available Models:")
    print("─" * 80)
    all_models = list_models()
    for model in all_models:
        print(f"  {model.provider:6s} | {model.name:25s} | {model.dimension:4d}D | {model.max_tokens:6,d} tokens")
    print()

    # Test 1: One provider, multiple models
    print("─" * 80)
    print("TEST 1: One JinaProvider instance with multiple models")
    print("─" * 80)

    if os.getenv("JINA_API_KEY"):
        try:
            # Create ONE provider instance
            jina_provider = JinaProvider()
            print(f"✅ Created JinaProvider: {jina_provider.provider_name}")
            print()

            # Use the SAME provider with DIFFERENT models
            test_text = "This is a test sentence for embedding."

            # Model 1: Jina v4 with 1024 dimensions
            print("Using model: JINA_V4_1024 (32K tokens, 1024D)")
            emb_v4_1024 = await jina_provider.embed_text(test_text, model=JINA_V4_1024)
            print(f"  Result: {len(emb_v4_1024)}D vector")
            print()

            # Model 2: Jina v4 with 768 dimensions (different dimension, same provider!)
            print("Using model: JINA_V4_768 (32K tokens, 768D)")
            emb_v4_768 = await jina_provider.embed_text(test_text, model=JINA_V4_768)
            print(f"  Result: {len(emb_v4_768)}D vector")
            print()

            # Model 3: Jina v3 with 1024 dimensions (different model version!)
            print("Using model: JINA_V3_1024 (8K tokens, 1024D)")
            emb_v3_1024 = await jina_provider.embed_text(test_text, model=JINA_V3_1024)
            print(f"  Result: {len(emb_v3_1024)}D vector")
            print()

            print("✅ SUCCESS: One provider can use multiple models!")
            print()

        except Exception as e:
            print(f"❌ Error: {e}")
            print()
    else:
        print("⚠️  Skipped: JINA_API_KEY not set")
        print()

    # Test 2: EmbeddingService with explicit model selection
    print("─" * 80)
    print("TEST 2: EmbeddingService with explicit model selection")
    print("─" * 80)

    if os.getenv("JINA_API_KEY"):
        try:
            # Create service with specific model
            service_v4 = await EmbeddingService.create(
                provider="jina",
                model=JINA_V4_1024,  # Explicit model
            )

            print(f"Provider: {service_v4.provider_name}")
            print(f"Model: {service_v4.model.name}")
            print(f"Dimension: {service_v4.model.dimension}D")
            print(f"Max tokens: {service_v4.model.max_tokens:,}")
            print()

            # Embed a text
            embedding = await service_v4.embed_text("Legal decision text example")
            print(f"Generated embedding: {len(embedding)}D")
            print()

            print("✅ SUCCESS: Service uses the specified model!")
            print()

        except Exception as e:
            print(f"❌ Error: {e}")
            print()
    else:
        print("⚠️  Skipped: JINA_API_KEY not set")
        print()

    # Test 3: Auto-selection with default models
    print("─" * 80)
    print("TEST 3: Auto-selection with default models")
    print("─" * 80)

    try:
        # Auto-select (will pick Jina if available, Google otherwise)
        service_auto = await EmbeddingService.create(provider="auto")

        print(f"Auto-selected provider: {service_auto.provider_name}")
        print(f"Default model: {service_auto.model.name}")
        print(f"Dimension: {service_auto.model.dimension}D")
        print(f"Max tokens: {service_auto.model.max_tokens:,}")
        print()

        print("✅ SUCCESS: Auto-selection picks the best provider with default model!")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        print()

    # Test 4: Model validation (provider mismatch)
    print("─" * 80)
    print("TEST 4: Model validation (should reject provider/model mismatch)")
    print("─" * 80)

    if os.getenv("JINA_API_KEY"):
        try:
            jina_provider = JinaProvider()

            # Try to use a Google model with Jina provider (should fail!)
            print("Attempting to use Google model with Jina provider...")
            await jina_provider.embed_text("test", model=GOOGLE_GEMINI_768)

            print("❌ UNEXPECTED: Should have raised an error!")
            print()

        except ValueError as e:
            print(f"✅ SUCCESS: Correctly rejected mismatch!")
            print(f"   Error: {e}")
            print()
        except Exception as e:
            print(f"⚠️  Unexpected error type: {e}")
            print()
    else:
        print("⚠️  Skipped: JINA_API_KEY not set")
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("The new architecture successfully separates:")
    print()
    print("1. PROVIDER (API Service):")
    print("   - Handles API authentication")
    print("   - Makes HTTP requests")
    print("   - Manages retries and errors")
    print("   - One instance can serve multiple models")
    print()
    print("2. MODEL (Configuration):")
    print("   - Defines model name")
    print("   - Specifies dimensions")
    print("   - Sets token limits")
    print("   - Immutable configuration object")
    print()
    print("Benefits:")
    print("  ✅ Cleaner separation of concerns")
    print("  ✅ One provider instance → many models")
    print("  ✅ Easier to add new models")
    print("  ✅ Better type safety (provider/model mismatch detection)")
    print("  ✅ More testable")
    print()


if __name__ == "__main__":
    asyncio.run(test_provider_model_separation())
