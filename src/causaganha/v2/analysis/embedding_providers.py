"""Embedding provider implementations (redirects to new architecture).

DEPRECATED: This module is kept for backward compatibility only.
New code should use:
- causaganha.v2.analysis.providers (Provider implementations)
- causaganha.v2.analysis.embedding_models (Model configurations)
- causaganha.v2.analysis.embedding_service_v2 (Service layer)
"""

# Re-export everything from the new providers module for backward compatibility
from causaganha.v2.analysis.providers import (
    EmbeddingProviderBase as EmbeddingModelBase,
    GoogleProvider as GoogleEmbeddingProvider,
    JinaProvider as JinaEmbeddingProvider,
    TaskType,
    auto_select_provider,
    create_provider as create_embedding_provider,
)

# Re-export the Protocol (keep for type checking)
from causaganha.v2.analysis.providers import EmbeddingProviderBase as EmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "EmbeddingModelBase",
    "GoogleEmbeddingProvider",
    "JinaEmbeddingProvider",
    "TaskType",
    "create_embedding_provider",
    "auto_select_provider",
]
