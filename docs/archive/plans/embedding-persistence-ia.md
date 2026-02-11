# Embedding Persistence to Internet Archive

## Problem Statement

Currently, embeddings are generated on-demand and discarded after use. This means:
- ❌ **Expensive reprocessing** if we need to regenerate embeddings
- ❌ **Wasted API costs** (Jina: $0.02/1M tokens, Google: $0.15/1M tokens)
- ❌ **Time-consuming** (~0.5-0.8s per embedding)
- ❌ **Rate limit pressure** during bulk operations

**Solution**: Save embeddings to Internet Archive alongside the judicial decision PDFs.

## Benefits

1. **Cost Savings**
   - Process once, use forever
   - No repeated API costs
   - Estimated savings: $1.40/month for 1M embeddings (if reprocessed monthly)

2. **Performance**
   - Instant retrieval from IA (no API call)
   - No rate limiting concerns
   - Parallel downloads possible

3. **Reproducibility**
   - Exact embeddings preserved
   - Version tracking (model version, date)
   - Audit trail for ratings

4. **Data Integrity**
   - Embeddings tied to specific PDF versions
   - No drift from model updates
   - Public transparency (IA is public)

## Architecture

### Current Flow

```
PDF (TJRO) → Download → Extract Text → Generate Embedding → Analyze → Discard Embedding
                 ↓
         Upload to IA (PDF only)
```

### Proposed Flow

```
PDF (TJRO) → Download → Extract Text → Generate Embedding → Analyze
                 ↓                              ↓
         Upload to IA (PDF)          Upload to IA (Embedding)
                                              ↓
                                      Metadata JSON with:
                                      - embedding vector
                                      - provider (jina/google)
                                      - model version
                                      - dimension
                                      - timestamp
                                      - PDF hash (link)
```

## Implementation Design

### 1. Embedding Storage Format

Store embeddings as JSON files alongside PDFs in Internet Archive.

**File structure**:
```
causaganha-{doc_id}/
├── decision.pdf                    # Original PDF
├── decision_embedding.json         # Embedding metadata + vector
└── metadata.json                   # Existing IA metadata
```

**Embedding JSON format**:
```json
{
  "version": "1.0",
  "pdf_identifier": "causaganha-abc123def456",
  "pdf_hash": "sha256:...",
  "generated_at": "2026-01-20T21:00:00Z",
  "provider": "jina",
  "model": "jina-embeddings-v3",
  "dimension": 1024,
  "embedding": [0.123, -0.456, 0.789, ...],  // 1024 floats
  "text_preview": "ACÓRDÃO: Vistos, relatados...",  // First 200 chars
  "tokens_used": 450,
  "task_type": "RETRIEVAL_DOCUMENT"
}
```

### 2. Storage Service Update

```python
# src/causaganha/v2/storage/embedding_storage.py

from pathlib import Path
import json
import hashlib
from datetime import datetime
from typing import Any

class EmbeddingStorage:
    """Store and retrieve embeddings from Internet Archive."""

    def __init__(self, ia_service):
        self.ia_service = ia_service

    async def save_embedding(
        self,
        ia_identifier: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> str:
        """Save embedding to Internet Archive.

        Args:
            ia_identifier: Internet Archive item identifier
            embedding: Embedding vector
            metadata: Additional metadata (provider, model, etc.)

        Returns:
            URL to the embedding file
        """
        embedding_data = {
            "version": "1.0",
            "pdf_identifier": ia_identifier,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "provider": metadata.get("provider"),
            "model": metadata.get("model"),
            "dimension": len(embedding),
            "embedding": embedding,
            "text_preview": metadata.get("text_preview", "")[:200],
            "tokens_used": metadata.get("tokens_used", 0),
            "task_type": metadata.get("task_type", "RETRIEVAL_DOCUMENT"),
        }

        # Add PDF hash if available
        if "pdf_hash" in metadata:
            embedding_data["pdf_hash"] = metadata["pdf_hash"]

        # Convert to JSON
        json_str = json.dumps(embedding_data, indent=2)
        json_bytes = json_str.encode("utf-8")

        # Upload to IA
        filename = f"{ia_identifier}_embedding.json"
        url = await self.ia_service.upload_file(
            identifier=ia_identifier,
            filename=filename,
            content=json_bytes,
            metadata={"collection": "causaganha-embeddings"},
        )

        return url

    async def load_embedding(self, ia_identifier: str) -> dict[str, Any] | None:
        """Load embedding from Internet Archive.

        Args:
            ia_identifier: Internet Archive item identifier

        Returns:
            Embedding data dict or None if not found
        """
        filename = f"{ia_identifier}_embedding.json"
        url = f"https://archive.org/download/{ia_identifier}/{filename}"

        try:
            # Download JSON
            content = await self.ia_service.download_file(url)
            return json.loads(content)
        except Exception as e:
            logger.warning("embedding_not_found", identifier=ia_identifier, error=str(e))
            return None

    def is_embedding_valid(
        self, embedding_data: dict[str, Any], required_model: str | None = None
    ) -> bool:
        """Check if cached embedding is still valid.

        Args:
            embedding_data: Loaded embedding data
            required_model: Required model version (None = any)

        Returns:
            True if embedding can be reused
        """
        # Check version compatibility
        if embedding_data.get("version") != "1.0":
            return False

        # Check model if specified
        if required_model and embedding_data.get("model") != required_model:
            return False

        # Check dimension
        if len(embedding_data.get("embedding", [])) != embedding_data.get("dimension"):
            return False

        return True
```

### 3. Pipeline Integration

```python
# src/causaganha/v2/pipeline/embedding_pipeline.py

class EmbeddingPipeline:
    def __init__(self, embedding_service, embedding_storage):
        self.service = embedding_service
        self.storage = embedding_storage

    async def get_or_create_embedding(
        self,
        text: str,
        ia_identifier: str,
        force_regenerate: bool = False,
    ) -> tuple[list[float], bool]:
        """Get cached embedding or generate new one.

        Args:
            text: Text to embed
            ia_identifier: IA identifier for caching
            force_regenerate: Skip cache, always generate

        Returns:
            (embedding, was_cached) tuple
        """
        # Try to load from cache
        if not force_regenerate:
            cached = await self.storage.load_embedding(ia_identifier)
            if cached and self.storage.is_embedding_valid(cached):
                logger.info(
                    "embedding_cache_hit",
                    identifier=ia_identifier,
                    model=cached.get("model"),
                )
                return cached["embedding"], True

        # Generate new embedding
        logger.info("embedding_cache_miss_generating", identifier=ia_identifier)
        embedding = await self.service.embed_text(text)

        # Save to IA
        metadata = {
            "provider": self.service.provider_name,
            "model": self.service.provider.model if hasattr(self.service.provider, 'model') else 'unknown',
            "text_preview": text[:200],
            "tokens_used": len(text) // 3,  # Rough estimate
            "task_type": "RETRIEVAL_DOCUMENT",
        }

        await self.storage.save_embedding(ia_identifier, embedding, metadata)

        logger.info(
            "embedding_generated_and_cached",
            identifier=ia_identifier,
            dimension=len(embedding),
        )

        return embedding, False
```

### 4. Migration Strategy

For existing PDFs without embeddings:

```python
# scripts/backfill_embeddings.py

async def backfill_embeddings(limit: int | None = None):
    """Generate and upload embeddings for existing PDFs.

    Args:
        limit: Maximum number to process (None = all)
    """
    # Query DuckDB for PDFs without embeddings
    decisions_without_embeddings = db.query("""
        SELECT pdf_url, ia_identifier, decision_text
        FROM decisions
        WHERE ia_identifier IS NOT NULL
        AND embedding_ia_url IS NULL
        LIMIT ?
    """, limit or 999999)

    pipeline = EmbeddingPipeline(embedding_service, embedding_storage)

    for decision in decisions_without_embeddings:
        embedding, _ = await pipeline.get_or_create_embedding(
            text=decision.decision_text,
            ia_identifier=decision.ia_identifier,
        )

        # Update database with embedding URL
        db.execute("""
            UPDATE decisions
            SET embedding_ia_url = ?,
                embedding_cached_at = ?
            WHERE ia_identifier = ?
        """, (
            f"https://archive.org/download/{decision.ia_identifier}/{decision.ia_identifier}_embedding.json",
            datetime.utcnow(),
            decision.ia_identifier,
        ))

    logger.info("backfill_complete", processed=len(decisions_without_embeddings))
```

## Database Schema Updates

Add columns to track embedding cache:

```sql
-- Add to decisions table
ALTER TABLE decisions ADD COLUMN embedding_ia_url TEXT;
ALTER TABLE decisions ADD COLUMN embedding_cached_at TIMESTAMP;
ALTER TABLE decisions ADD COLUMN embedding_provider TEXT;  -- 'jina' or 'google'
ALTER TABLE decisions ADD COLUMN embedding_model TEXT;     -- 'jina-embeddings-v3'
ALTER TABLE decisions ADD COLUMN embedding_dimension INT;  -- 1024
```

## Cost Analysis

### Storage Costs

**Internet Archive**: FREE (non-profit, unlimited storage for public data)

**Embedding size**:
- 1024 dimensions × 4 bytes (float32) = 4 KB raw
- + JSON metadata ≈ 1 KB
- **Total: ~5 KB per embedding**

**Volume projection**:
- 1 million decisions
- 5 KB × 1M = 5 GB total
- **IA cost: $0** (free for public data)

### API Cost Savings

**Without caching**:
- Reprocess monthly: 1M embeddings × $0.02/1K = $20/month
- Reprocess for analysis updates: Additional $20-40/month
- **Total waste: $20-60/month**

**With caching**:
- Process once: $0.02 (one-time)
- Retrieval: FREE from IA
- **Savings: $20-60/month** ✅

## Performance Impact

### Embedding Generation (First Time)
- Current: ~0.5-0.8s per embedding (Jina API)
- With caching: Same (first time only)

### Embedding Retrieval (Cached)
- Download 5 KB JSON from IA: ~0.1-0.2s
- **5-8x faster than API generation** ✅

### Bulk Processing (100K decisions)
- Without cache: 100K × 0.6s = 60,000s = **16.7 hours**
- With 90% cache hit: 10K × 0.6s + 90K × 0.15s = **3.75 hours** ✅
- **4.5x faster bulk processing**

## Versioning & Compatibility

### Handling Model Updates

When embedding models update (e.g., jina-embeddings-v3 → v4):

```python
def should_regenerate_embedding(cached_data: dict, current_model: str) -> bool:
    """Check if embedding should be regenerated.

    Args:
        cached_data: Cached embedding metadata
        current_model: Current model being used

    Returns:
        True if regeneration needed
    """
    # Major version change → regenerate
    if cached_data["model"].split("-")[0] != current_model.split("-")[0]:
        return True

    # Different provider → regenerate
    if get_provider_from_model(cached_data["model"]) != get_provider_from_model(current_model):
        return True

    # Dimension mismatch → regenerate
    if cached_data["dimension"] != get_model_dimension(current_model):
        return True

    return False
```

### Gradual Migration

```python
# Allow gradual re-embedding without breaking existing functionality
async def get_embedding_with_fallback(
    text: str,
    ia_identifier: str,
    preferred_model: str = "jina-embeddings-v3",
) -> list[float]:
    """Get embedding, prefer cached but allow fallback.

    Priority:
    1. Cached embedding (exact model match)
    2. Cached embedding (compatible model)
    3. Generate new embedding
    """
    cached = await storage.load_embedding(ia_identifier)

    # Exact match
    if cached and cached["model"] == preferred_model:
        return cached["embedding"]

    # Compatible match (same provider, similar dimension)
    if cached and is_compatible(cached["model"], preferred_model):
        logger.info("using_compatible_cached_embedding")
        return cached["embedding"]

    # Generate new
    return await generate_and_cache(text, ia_identifier, preferred_model)
```

## Compliance & Transparency

### LGPD Compliance

Per `docs/COMPLIANCE.md`:
- ✅ **Embeddings are derived from public court records** (no personal data)
- ✅ **Uploading to IA increases transparency** (public audit trail)
- ✅ **Links embedding to specific PDF version** (data provenance)

### Public Access

All embeddings stored in Internet Archive are:
- ✅ **Publicly accessible** (matching our transparency mission)
- ✅ **Permanently archived** (cannot be deleted after processing)
- ✅ **Auditable** (anyone can verify our embeddings match the PDFs)

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Create `EmbeddingStorage` class
- [ ] Add database schema columns
- [ ] Implement save/load functions
- [ ] Write unit tests

### Phase 2: Pipeline Integration (Week 2)
- [ ] Update `EmbeddingPipeline` with caching logic
- [ ] Add cache hit/miss logging
- [ ] Implement backfill script
- [ ] Test with 100 decisions

### Phase 3: Backfill (Week 3)
- [ ] Run backfill for all existing decisions
- [ ] Monitor IA upload success rate
- [ ] Verify embedding retrieval
- [ ] Update monitoring dashboard

### Phase 4: Production (Week 4)
- [ ] Enable caching by default
- [ ] Set up cache hit rate metrics
- [ ] Document versioning strategy
- [ ] Create migration guide for model updates

## Monitoring & Metrics

Track the following metrics:

```python
# Add to monitoring
metrics = {
    "embedding_cache_hit_rate": 0.0,  # % of embeddings loaded from cache
    "embedding_generation_time_avg": 0.0,  # seconds
    "embedding_retrieval_time_avg": 0.0,  # seconds
    "embedding_storage_failures": 0,
    "embedding_ia_uploads_total": 0,
    "embedding_api_cost_saved": 0.0,  # USD
}
```

## Alternative Considerations

### Why Not DuckDB Only?

**Cons of local-only storage**:
- ❌ Not publicly accessible (less transparent)
- ❌ Single point of failure (no redundancy)
- ❌ Harder to share with community
- ❌ Not permanent (could be lost)

**Hybrid approach** (Recommended):
- Store in DuckDB for fast local access
- Upload to IA for permanence and transparency
- Best of both worlds ✅

### Why Not S3/GCS?

**Cons of cloud storage**:
- ❌ Monthly costs ($0.023/GB/month for S3)
- ❌ Egress fees ($0.09/GB for downloads)
- ❌ Not aligned with transparency mission

**IA advantages**:
- ✅ FREE storage
- ✅ FREE bandwidth
- ✅ Non-profit, permanent archive
- ✅ Aligns with public data mission

## Success Criteria

✅ **Cost Savings**: Save >$10/month on embedding re-generation
✅ **Performance**: 90%+ cache hit rate after initial backfill
✅ **Reliability**: 99%+ successful IA uploads
✅ **Transparency**: All embeddings publicly verifiable on archive.org
✅ **Compatibility**: Seamless model version transitions

## References

- [Internet Archive Upload API](https://archive.org/services/docs/api/items.html)
- [Existing PreservationService](../src/causaganha/infrastructure/clients/preservation.py)
- [COMPLIANCE.md](../COMPLIANCE.md) - Legal considerations
- [EMBEDDING_PROVIDERS.md](../EMBEDDING_PROVIDERS.md) - Provider comparison

---

**Status**: Planning
**Priority**: High (significant cost savings)
**Estimated Effort**: 3-4 weeks (4 phases)
**ROI**: $20-60/month savings + 4.5x faster bulk processing
