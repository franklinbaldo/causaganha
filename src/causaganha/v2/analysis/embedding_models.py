"""Embedding model configurations for different providers.

This module defines embedding models (configuration) separately from providers (API services).
Each model specifies its name, dimensions, token limits, and provider.
"""

from dataclasses import dataclass
from typing import Literal


ProviderType = Literal["jina", "google"]


@dataclass(frozen=True)
class EmbeddingModel:
    """Configuration for a specific embedding model.

    This class represents the configuration and capabilities of an embedding model,
    separate from the provider (API service) that hosts it.

    Attributes:
        provider: Provider name ('jina' or 'google')
        name: Model name (e.g., 'jina-embeddings-v4')
        dimension: Embedding dimension (e.g., 1024)
        max_tokens: Maximum tokens the model can process
        description: Human-readable description
    """

    provider: ProviderType
    name: str
    dimension: int
    max_tokens: int
    description: str = ""

    def __repr__(self) -> str:
        """Return a string representation of the model."""
        return (
            f"EmbeddingModel(provider='{self.provider}', name='{self.name}', "
            f"dimension={self.dimension}, max_tokens={self.max_tokens})"
        )


# Jina AI Models
JINA_V4_1024 = EmbeddingModel(
    provider="jina",
    name="jina-embeddings-v4",
    dimension=1024,
    max_tokens=32768,  # 32K tokens
    description="Jina v4 with 1024 dimensions (recommended for legal documents)",
)

JINA_V4_768 = EmbeddingModel(
    provider="jina",
    name="jina-embeddings-v4",
    dimension=768,
    max_tokens=32768,  # 32K tokens
    description="Jina v4 with 768 dimensions (compatible with Google)",
)

JINA_V4_512 = EmbeddingModel(
    provider="jina",
    name="jina-embeddings-v4",
    dimension=512,
    max_tokens=32768,  # 32K tokens
    description="Jina v4 with 512 dimensions (smaller, faster)",
)

JINA_V3_1024 = EmbeddingModel(
    provider="jina",
    name="jina-embeddings-v3",
    dimension=1024,
    max_tokens=8192,  # 8K tokens
    description="Jina v3 with 1024 dimensions (legacy)",
)

JINA_V3_768 = EmbeddingModel(
    provider="jina",
    name="jina-embeddings-v3",
    dimension=768,
    max_tokens=8192,  # 8K tokens
    description="Jina v3 with 768 dimensions (legacy)",
)

JINA_V2_768 = EmbeddingModel(
    provider="jina",
    name="jina-embeddings-v2",
    dimension=768,
    max_tokens=8192,  # 8K tokens
    description="Jina v2 (deprecated, fixed 768D)",
)

# Google AI Models
GOOGLE_GEMINI_768 = EmbeddingModel(
    provider="google",
    name="gemini-embedding-001",
    dimension=768,
    max_tokens=2048,  # 2K tokens (limitation for legal docs)
    description="Google Gemini embedding (768D)",
)

GOOGLE_GEMINI_3072 = EmbeddingModel(
    provider="google",
    name="gemini-embedding-001",
    dimension=3072,
    max_tokens=2048,  # 2K tokens
    description="Google Gemini embedding (max 3072D)",
)

GOOGLE_TEXT_EMBEDDING_004 = EmbeddingModel(
    provider="google",
    name="text-embedding-004",
    dimension=768,
    max_tokens=768,  # Very limited
    description="Google text-embedding-004 (deprecated August 2025)",
)

# Default models for each provider
DEFAULT_JINA_MODEL = JINA_V4_1024
DEFAULT_GOOGLE_MODEL = GOOGLE_GEMINI_768

# Model registry for lookup by name and dimension
JINA_MODELS = {
    ("jina-embeddings-v4", 1024): JINA_V4_1024,
    ("jina-embeddings-v4", 768): JINA_V4_768,
    ("jina-embeddings-v4", 512): JINA_V4_512,
    ("jina-embeddings-v3", 1024): JINA_V3_1024,
    ("jina-embeddings-v3", 768): JINA_V3_768,
    ("jina-embeddings-v2", 768): JINA_V2_768,
}

GOOGLE_MODELS = {
    ("gemini-embedding-001", 768): GOOGLE_GEMINI_768,
    ("gemini-embedding-001", 3072): GOOGLE_GEMINI_3072,
    ("text-embedding-004", 768): GOOGLE_TEXT_EMBEDDING_004,
}

ALL_MODELS = {**JINA_MODELS, **GOOGLE_MODELS}


def get_model(provider: ProviderType, name: str, dimension: int) -> EmbeddingModel:
    """Get an embedding model by provider, name, and dimension.

    Args:
        provider: Provider name ('jina' or 'google')
        name: Model name
        dimension: Embedding dimension

    Returns:
        EmbeddingModel instance

    Raises:
        ValueError: If model is not found
    """
    key = (name, dimension)

    if provider == "jina":
        model = JINA_MODELS.get(key)
    elif provider == "google":
        model = GOOGLE_MODELS.get(key)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    if model is None:
        raise ValueError(
            f"Model not found: {provider}/{name} with {dimension}D. "
            f"Available models: {list(JINA_MODELS.keys() if provider == 'jina' else GOOGLE_MODELS.keys())}",
        )

    return model


def get_default_model(provider: ProviderType) -> EmbeddingModel:
    """Get the default model for a provider.

    Args:
        provider: Provider name ('jina' or 'google')

    Returns:
        Default EmbeddingModel for that provider
    """
    if provider == "jina":
        return DEFAULT_JINA_MODEL
    if provider == "google":
        return DEFAULT_GOOGLE_MODEL
    raise ValueError(f"Unknown provider: {provider}")


def list_models(provider: ProviderType | None = None) -> list[EmbeddingModel]:
    """List all available models, optionally filtered by provider.

    Args:
        provider: Optional provider filter ('jina', 'google', or None for all)

    Returns:
        List of available EmbeddingModel instances
    """
    if provider is None:
        return list(ALL_MODELS.values())
    if provider == "jina":
        return list(JINA_MODELS.values())
    if provider == "google":
        return list(GOOGLE_MODELS.values())
    raise ValueError(f"Unknown provider: {provider}")
