# CausaGanha Experiments

This directory contains documentation for experiments and proof-of-concepts conducted on the CausaGanha platform.

## Completed Experiments

### 1. Local Embeddings Experiment (2026-01-22)
**Status:** ✅ Successful - Recommended for production

**Summary:** Evaluated local CPU-optimized embedding models (sentence-transformers) vs Jina AI API for generating embeddings of Brazilian legal documents.

**Key Findings (Performance):**
- **40x faster** latency (15ms vs 606ms)
- **61x higher** throughput (54 texts/s vs 0.88 texts/s)
- **Zero API costs** ($0 vs ~$480/year)
- **Complete data privacy** (LGPD compliant)
- **No rate limits** (Jina hit limits during testing)

**Key Findings (Quality):**
- **Precision@10:** 0.500 (good - 50% relevant results)
- **Recall@10:** 0.379 (moderate - finds 38% of docs)
- **NDCG@10:** 0.561 (good ranking quality)
- **MRR:** 0.728 (first relevant result early)

**Recommendation:** Use local embeddings as default provider

**Details:**
- Performance analysis: [local-embeddings-experiment.md](./local-embeddings-experiment.md)
- Quality benchmark guide: [embedding-quality-benchmark-guide.md](./embedding-quality-benchmark-guide.md)

**Implementation:**
- ✅ LocalProvider implemented in `src/causaganha/v2/analysis/providers.py`
- ✅ Local models added to `src/causaganha/v2/analysis/embedding_models.py`
- ✅ Benchmark script: `scripts/benchmark_embeddings.py`
- ✅ Config updated: `EMBEDDING_PROVIDER_PRIORITY = ["local", "jina", "google"]`

**Usage:**
```python
from causaganha.v2.analysis.embedding_service_v2 import EmbeddingService

# Auto-select (will use local by default)
service = await EmbeddingService.create()

# Force local provider
service = await EmbeddingService.create(provider="local")

# Generate embeddings
embedding = await service.embed_text("Sentença procedente.")
```

**Benchmark Results:**
```bash
# Run full benchmark
uv run python scripts/benchmark_embeddings.py --providers local --providers jina

# Quick test
uv run python scripts/benchmark_embeddings.py --providers local --sample-size 5
```

---

## Experiment Template

When conducting new experiments, create a document with:

1. **Problem Statement** - What are we trying to solve?
2. **Hypothesis** - What do we expect to find?
3. **Methodology** - How will we test it?
4. **Results** - What did we discover?
5. **Recommendation** - What should we do?
6. **Next Steps** - What follows this experiment?

See [local-embeddings-experiment.md](./local-embeddings-experiment.md) as an example.
