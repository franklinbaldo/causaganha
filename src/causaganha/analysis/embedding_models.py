"""Embedding model configurations for different providers.

This module defines embedding models (configuration) separately from providers (API services).
Each model specifies its name, dimensions, token limits, and provider.
"""

from dataclasses import dataclass
from typing import Literal


ProviderType = Literal["jina"]


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

# Default models for each provider
DEFAULT_JINA_MODEL = JINA_V4_1024


def get_default_model(provider: ProviderType) -> EmbeddingModel:
    """Get the default model for a provider.

    Args:
        provider: Provider name ('jina')

    Returns:
        Default EmbeddingModel for that provider
    """
    if provider == "jina":
        return DEFAULT_JINA_MODEL
    msg = f"Unknown provider: {provider}"
    raise ValueError(msg)
