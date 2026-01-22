"""Embedding service (redirects to new architecture).

DEPRECATED: This module redirects to the new embedding_service_v2 module.
All new code should import from embedding_service_v2 directly.
"""

# Re-export everything from the new service for backward compatibility
from causaganha.v2.analysis.embedding_service_v2 import (
    CONTEXTUAL_PREFIX,
    EmbeddingService,
    TaskType,
)


__all__ = [
    "CONTEXTUAL_PREFIX",
    "EmbeddingService",
    "TaskType",
]
