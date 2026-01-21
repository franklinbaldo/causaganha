# Provider + Model Architecture

## Overview

The embedding system has been refactored to separate **Provider** (API service) from **Model** (configuration). This follows the Single Responsibility Principle and makes the codebase more maintainable and extensible.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    EmbeddingService                         │
│  - Orchestrates provider and model                         │
│  - Handles chunking and batch processing                   │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
             ▼                            ▼
    ┌────────────────┐          ┌─────────────────┐
    │   Provider     │          │     Model       │
    │  (API Service) │          │ (Configuration) │
    ├────────────────┤          ├─────────────────┤
    │ - JinaProvider │          │ - name          │
    │ - GoogleProvider│         │ - dimension     │
    │                │          │ - max_tokens    │
    │ Handles:       │          │ - description   │
    │ • Auth         │          └─────────────────┘
    │ • HTTP         │
    │ • Retries      │                ▲
    │ • Errors       │                │
    └────────────────┘                │
             │                        │
             │    Uses model config   │
             └────────────────────────┘
```

## Key Concepts

### Provider (API Service)

**Responsibility**: Handle API communication

```python
class JinaProvider(EmbeddingProviderBase):
    """Jina AI API service."""

    def __init__(self, api_key: str | None = None):
        # Setup API connection, authentication

    async def embed_text(
        self,
        text: str,
        model: EmbeddingModel,  # ← Receives model configuration
        task_type: TaskType
    ) -> list[float]:
        # Makes API call using model.name, model.dimension
```

**Key Points**:
- One instance can serve multiple models
- Handles authentication, retries, error handling
- Stateless (no model configuration stored)
- Reusable across different model configurations

### Model (Configuration)

**Responsibility**: Define embedding model characteristics

```python
@dataclass(frozen=True)
class EmbeddingModel:
    """Immutable model configuration."""
    provider: ProviderType      # 'jina' or 'google'
    name: str                   # 'jina-embeddings-v4'
    dimension: int              # 1024
    max_tokens: int             # 32768
    description: str            # Human-readable description
```

**Key Points**:
- Immutable (frozen dataclass)
- No business logic, just data
- Predefined instances (JINA_V4_1024, GOOGLE_GEMINI_768, etc.)
- Easy to add new models without changing provider code

## Predefined Models

### Jina AI Models

```python
from causaganha.v2.analysis.embedding_models import (
    JINA_V4_1024,   # Recommended for legal documents (32K tokens)
    JINA_V4_768,    # Compatible with Google dimensions
    JINA_V4_512,    # Smaller, faster
    JINA_V3_1024,   # Legacy (8K tokens)
    JINA_V3_768,    # Legacy
    JINA_V2_768,    # Deprecated
)
```

### Google AI Models

```python
from causaganha.v2.analysis.embedding_models import (
    GOOGLE_GEMINI_768,    # Standard (2K tokens)
    GOOGLE_GEMINI_3072,   # High-dimensional (2K tokens)
    GOOGLE_TEXT_EMBEDDING_004,  # Deprecated
)
```

### Default Models

```python
DEFAULT_JINA_MODEL = JINA_V4_1024     # 32K tokens, 1024D
DEFAULT_GOOGLE_MODEL = GOOGLE_GEMINI_768  # 2K tokens, 768D
```

## Usage Examples

### Example 1: Auto-selection with default model

```python
from causaganha.v2.analysis.embedding_service_v2 import EmbeddingService

# Auto-select provider, use default model
service = await EmbeddingService.create()

# Generates embedding using:
# - Best available provider (Jina > Google)
# - Default model for that provider
embedding = await service.embed_text("Legal decision text")
```

### Example 2: Specific provider with custom model

```python
from causaganha.v2.analysis.embedding_models import JINA_V4_768
from causaganha.v2.analysis.embedding_service_v2 import EmbeddingService

# Use Jina with 768D model (compatible with Google)
service = await EmbeddingService.create(
    provider="jina",
    model=JINA_V4_768
)

embedding = await service.embed_text("Text")
print(len(embedding))  # 768
```

### Example 3: One provider, multiple models

```python
from causaganha.v2.analysis.providers import JinaProvider
from causaganha.v2.analysis.embedding_models import (
    JINA_V4_1024,
    JINA_V4_768,
    JINA_V3_1024,
)

# Create ONE provider instance
jina = JinaProvider()

# Use SAME provider with DIFFERENT models
emb_1024d = await jina.embed_text("text", model=JINA_V4_1024)  # 1024D
emb_768d = await jina.embed_text("text", model=JINA_V4_768)    # 768D
emb_v3 = await jina.embed_text("text", model=JINA_V3_1024)     # v3 model

print(len(emb_1024d))  # 1024
print(len(emb_768d))   # 768
print(len(emb_v3))     # 1024 (but different model version)
```

### Example 4: Dynamic chunking with model token limits

```python
from causaganha.v2.analysis.embedding_service_v2 import EmbeddingService
from causaganha.v2.analysis.embedding_models import JINA_V4_1024

# Create service with Jina v4 (32K token limit)
service = await EmbeddingService.create(
    provider="jina",
    model=JINA_V4_1024
)

# Chunking adapts to model's 32K token limit
long_decision_text = "..." * 10000  # Very long legal decision
chunks_and_embeddings = await service.embed_chunked_text(
    long_decision_text,
    strategy="auto"  # Uses semantic sections for legal docs
)

# With Jina v4: Entire decision in 1-2 chunks
# With Google: Would require 10-20+ chunks (2K limit)
```

### Example 5: Adding a new model

```python
# In embedding_models.py

# Add a new model configuration
JINA_V4_256 = EmbeddingModel(
    provider="jina",
    name="jina-embeddings-v4",
    dimension=256,  # Smaller dimension
    max_tokens=32768,
    description="Jina v4 with 256 dimensions (fastest)"
)

# Register in the model registry
JINA_MODELS = {
    # ... existing models ...
    ("jina-embeddings-v4", 256): JINA_V4_256,  # ← Add here
}

# That's it! No provider code changes needed.
# Now you can use it:
service = await EmbeddingService.create(
    provider="jina",
    model=JINA_V4_256  # ← New model works immediately
)
```

## Benefits of This Architecture

### 1. Separation of Concerns

**Before**: Provider mixed with model configuration
```python
provider = JinaEmbeddingProvider(
    model="jina-embeddings-v4",  # ❌ Configuration in provider
    dimension=1024,              # ❌ Configuration in provider
)
```

**After**: Clean separation
```python
provider = JinaProvider()  # ✅ Just API service
model = JINA_V4_1024       # ✅ Just configuration
```

### 2. Reusability

**Before**: One provider instance per model
```python
provider_1024 = JinaEmbeddingProvider(dimension=1024)
provider_768 = JinaEmbeddingProvider(dimension=768)  # ❌ Duplicate API connection
```

**After**: One provider, many models
```python
provider = JinaProvider()  # ✅ Single API connection
emb_1024 = await provider.embed_text(text, JINA_V4_1024)
emb_768 = await provider.embed_text(text, JINA_V4_768)
```

### 3. Extensibility

**Before**: Add new model → modify provider class
```python
class JinaEmbeddingProvider:
    MODEL_TOKEN_LIMITS = {
        "jina-embeddings-v4": 32768,
        "jina-embeddings-v5": ???,  # ❌ Need to modify class
    }
```

**After**: Add new model → create model instance
```python
# In embedding_models.py
JINA_V5_1024 = EmbeddingModel(
    provider="jina",
    name="jina-embeddings-v5",
    dimension=1024,
    max_tokens=65536,
    description="Jina v5 (hypothetical)"
)
# ✅ No provider code changes!
```

### 4. Type Safety

**Before**: No validation of provider/model compatibility
```python
# This would fail at runtime
provider = JinaEmbeddingProvider(model="gemini-embedding-001")  # ❌ Wrong model for provider
```

**After**: Compile-time and runtime validation
```python
jina = JinaProvider()
await jina.embed_text("text", GOOGLE_GEMINI_768)
# ✅ Raises ValueError: "JinaProvider requires a Jina model, got google/gemini-embedding-001"
```

### 5. Testability

**Before**: Tightly coupled, hard to mock
```python
# Hard to test different model configs without creating provider instances
```

**After**: Easy to test with mock providers and real models
```python
# Test with mock provider
mock_provider = MockProvider()
result = await mock_provider.embed_text("text", JINA_V4_1024)

# Test model configurations independently
assert JINA_V4_1024.max_tokens == 32768
assert GOOGLE_GEMINI_768.max_tokens == 2048
```

## Migration Guide

### Old Code (embedding_providers.py, embedding_service.py)

```python
from causaganha.v2.analysis.embedding_service import EmbeddingService

# Old way
service = EmbeddingService(
    provider="jina",
    model="jina-embeddings-v4",
    dimension=1024,
)
```

### New Code (providers.py, embedding_models.py, embedding_service_v2.py)

```python
from causaganha.v2.analysis.embedding_service_v2 import EmbeddingService
from causaganha.v2.analysis.embedding_models import JINA_V4_1024

# New way
service = await EmbeddingService.create(
    provider="jina",
    model=JINA_V4_1024,
)
```

**Note**: Old code still works for backward compatibility. New features will only be added to the new architecture.

## File Structure

```
src/causaganha/v2/analysis/
├── embedding_models.py          # ← NEW: Model configurations
├── providers.py                 # ← NEW: Provider implementations
├── embedding_service_v2.py      # ← NEW: Service using new architecture
│
├── embedding_providers.py       # ← OLD: Legacy (backward compatibility)
└── embedding_service.py         # ← OLD: Legacy (backward compatibility)
```

## When to Use Which

### Use New Architecture When:
- ✅ Building new features
- ✅ Need to use multiple models with one provider
- ✅ Want better type safety
- ✅ Working on provider/model extensibility

### Use Old Architecture When:
- ⚠️ Maintaining existing legacy code
- ⚠️ Backward compatibility required
- ⚠️ Gradual migration in progress

## Future Enhancements

Possible improvements with this architecture:

1. **Model Versioning**: Track model versions for reproducibility
2. **Model Caching**: Cache model metadata for faster lookups
3. **Model Aliases**: Allow friendly names (`jina-large`, `jina-small`)
4. **Model Validation**: Validate model configs at startup
5. **Model Metrics**: Track usage stats per model
6. **Custom Models**: Allow users to define custom model configs
7. **Model Migration**: Tools to migrate between model versions

## References

- [Jina AI Models](https://jina.ai/embeddings/)
- [Google Gemini Embedding Models](https://ai.google.dev/gemini-api/docs/embeddings)
- [EMBEDDING_PROVIDERS.md](./EMBEDDING_PROVIDERS.md) - Provider comparison
- [Single Responsibility Principle](https://en.wikipedia.org/wiki/Single-responsibility_principle)

---

**Created**: 2026-01-21
**Status**: ✅ Production-ready
**Backward Compatible**: Yes (old architecture still supported)
