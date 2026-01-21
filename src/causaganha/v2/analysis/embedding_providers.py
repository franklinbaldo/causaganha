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
)

# Re-export the Protocol (keep for type checking)
from causaganha.v2.analysis.providers import EmbeddingProviderBase as EmbeddingProvider
from causaganha.v2.analysis.providers import (
    GoogleProvider as GoogleEmbeddingProvider,
)
from causaganha.v2.analysis.providers import (
    JinaProvider as JinaEmbeddingProvider,
)
from causaganha.v2.analysis.providers import (
    TaskType,
    auto_select_provider,
)
from causaganha.v2.analysis.providers import (
    create_provider as create_embedding_provider,
)


__all__ = [
    "EmbeddingModelBase",
    "EmbeddingProvider",
    "GoogleEmbeddingProvider",
    "JinaEmbeddingProvider",
    "TaskType",
    "auto_select_provider",
    "create_embedding_provider",
]
