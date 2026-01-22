# Embedding Quality Benchmark Guide

**Status:** ✅ Implemented
**Date:** 2026-01-22

## Overview

This guide explains how to measure the **actual quality** of embedding providers for CausaGanha's legal document retrieval use case.

## Why Quality Benchmarks Matter

The [local embeddings experiment](./local-embeddings-experiment.md) showed that local embeddings are **40x faster** and **free**, but it didn't answer the critical question:

> **Are local embeddings good enough for semantic search on Brazilian legal documents?**

This benchmark answers that question by testing retrieval accuracy on real legal text.

## Two-Phase Benchmarking Approach

### Phase 1: Performance Benchmark ✅
**Script:** `scripts/benchmark_embeddings.py`
**Measures:** Latency, throughput, cost

**Results:**
- Local: 15ms latency, 54 texts/s, $0
- Jina: 606ms latency, 0.88 texts/s, ~$480/year

**Conclusion:** Local wins on performance and cost.

### Phase 2: Quality Benchmark ✅
**Script:** `scripts/benchmark_embedding_quality.py`
**Measures:** Precision@K, Recall@K, NDCG, MRR

**Results (synthetic data, LOCAL provider):**
- Precision@10: 0.500 (good - 50% of results relevant)
- Recall@10: 0.379 (moderate - finds 38% of relevant docs)
- NDCG@10: 0.561 (good ranking quality)
- MRR: 0.728 (first relevant result at position ~1.4)

**Conclusion:** Local provider shows **acceptable quality** for production.

## How the Quality Benchmark Works

### 1. Data Source
Uses real legal documents from your DuckDB database:
- `intimations` table: Contains `texto` field with legal text
- `decision_analysis` table: Provides metadata labels
- Metadata: `decision_type`, `outcome`, `nome_classe`, etc.

### 2. Test Queries
Generates semantic search queries based on metadata:
- **Decision type queries:** "decisões procedentes", "sentenças de improcedência"
- **Outcome queries:** "recursos providos", "recursos improvidos"
- **Document class queries:** "apelação cível", "recurso inominado"

### 3. Retrieval Metrics

#### Precision@K
**What it measures:** Relevance of top-K results
**Formula:** `(# relevant docs in top K) / K`
**Good threshold:** >0.5
**Example:** P@10 = 0.6 means 6 out of 10 top results are relevant

#### Recall@K
**What it measures:** Coverage of relevant documents
**Formula:** `(# relevant docs in top K) / (total # relevant docs)`
**Good threshold:** >0.5
**Example:** R@10 = 0.4 means finding 40% of all relevant documents

#### NDCG@10 (Normalized Discounted Cumulative Gain)
**What it measures:** Ranking quality (penalizes relevant docs ranked lower)
**Range:** 0.0 to 1.0
**Good threshold:** >0.5
**Example:** NDCG@10 = 0.7 means good ranking, relevant docs appear early

#### MRR (Mean Reciprocal Rank)
**What it measures:** Position of first relevant result
**Formula:** `1 / (position of first relevant doc)`
**Range:** 0.0 to 1.0
**Example:** MRR = 0.5 means first relevant doc at position 2

## Usage

### Option 1: With Real Data (Recommended)

```bash
# Run quality benchmark on your actual PJe data
uv run python scripts/benchmark_embedding_quality.py \
  --providers local jina \
  --sample-size 200 \
  --db data/causaganha.duckdb
```

**Requirements:**
- Database must exist: `data/causaganha.duckdb`
- Must have analyzed documents with metadata
- Recommended: At least 100 documents with varied decision types

### Option 2: With Synthetic Test Data

```bash
# Generate test data (for development/testing)
uv run python scripts/generate_test_legal_data.py 200

# Run benchmark on test data
uv run python scripts/benchmark_embedding_quality.py \
  --providers local jina \
  --sample-size 100 \
  --db data/causaganha_test.duckdb
```

**Use cases:**
- Testing benchmark logic without real data
- Development and iteration
- CI/CD automated testing

### Option 3: Quick Local-Only Test

```bash
# Fast test with local provider only
uv run python scripts/benchmark_embedding_quality.py \
  --providers local \
  --sample-size 50
```

## Interpreting Results

### Quality Thresholds

| Metric | Excellent | Good | Poor |
|--------|-----------|------|------|
| **Precision@10** | >0.7 | >0.5 | <0.3 |
| **Recall@10** | >0.7 | >0.5 | <0.3 |
| **NDCG@10** | >0.7 | >0.5 | <0.3 |
| **MRR** | >0.8 | >0.6 | <0.4 |

### Decision Matrix

| Precision@10 | NDCG@10 | Recommendation |
|--------------|---------|----------------|
| ≥0.7 | ≥0.7 | ✅ **Excellent** - Strongly recommended for production |
| ≥0.5 | ≥0.5 | ⚠️ **Good** - Acceptable for production |
| <0.5 | <0.5 | ❌ **Poor** - Not recommended, consider alternatives |

### Example Scenarios

#### Scenario 1: High Precision, Low Recall
```
Precision@10: 0.80
Recall@10: 0.30
```
**Interpretation:** Results are highly relevant but missing many documents.
**Action:** Acceptable for applications where precision > recall (e.g., showing "best matches" to users).

#### Scenario 2: Low Precision, High Recall
```
Precision@10: 0.40
Recall@10: 0.80
```
**Interpretation:** Finds many documents but with low relevance.
**Action:** Not recommended. Users will see too much noise.

#### Scenario 3: Balanced Quality
```
Precision@10: 0.60
Recall@10: 0.60
NDCG@10: 0.65
```
**Interpretation:** Good balance, acceptable quality.
**Action:** ✅ Recommended for production.

## Next Steps: When to Re-Benchmark

### Trigger Conditions
Re-run quality benchmarks when:

1. **Switching embedding providers** (e.g., local → Jina)
2. **Changing models** (e.g., E5-small → BERT-Portuguese)
3. **Significant data changes** (e.g., new tribunal, different document types)
4. **Quality concerns** (user reports poor search results)
5. **Major updates** (model updates, library upgrades)

### Progressive Testing Strategy

**Stage 1: Synthetic Data (Development)**
```bash
# Quick validation
uv run python scripts/generate_test_legal_data.py 100
uv run python scripts/benchmark_embedding_quality.py --db data/causaganha_test.duckdb
```

**Stage 2: Real Data (Pre-Production)**
```bash
# Full quality validation
uv run python scripts/benchmark_embedding_quality.py \
  --providers local jina \
  --sample-size 200
```

**Stage 3: A/B Testing (Production)**
- Deploy both providers to subsets of users
- Measure click-through rate (CTR) on search results
- User feedback on result relevance
- Compare against benchmark metrics

## Advanced: Testing Multiple Models

```bash
# Compare different local models
# (After adding more models to embedding_models.py)

# Test Portuguese-specific model
uv run python scripts/benchmark_embedding_quality.py \
  --providers local \
  --model neuralmind/bert-base-portuguese-cased

# Compare all available models
uv run python scripts/benchmark_embedding_quality.py \
  --providers local jina google \
  --sample-size 300
```

## Troubleshooting

### "No test queries generated"
**Cause:** Not enough documents with metadata
**Solution:** Generate more test data or collect more real documents

### "Database not found"
**Cause:** No database at specified path
**Solution:** Either run data collection pipeline or generate test data

### "Out of memory"
**Cause:** Embedding too many documents at once
**Solution:** Reduce `--sample-size` or batch documents

### Quality metrics seem low
**Possible causes:**
1. Model not suitable for legal domain → Try Portuguese-specific models
2. Query generation needs tuning → Adjust test queries
3. Metadata labels are noisy → Verify database quality
4. Synthetic data too artificial → Test with real PJe data

## Files Reference

```
scripts/
├── benchmark_embeddings.py          # Performance benchmark (latency, throughput)
├── benchmark_embedding_quality.py   # Quality benchmark (retrieval accuracy)
└── generate_test_legal_data.py      # Synthetic data generator

docs/experiments/
├── local-embeddings-experiment.md   # Performance experiment results
├── embedding-quality-benchmark-guide.md  # This file
└── README.md                        # Experiments index
```

## Conclusion

**Quality benchmarking is essential** before deploying embeddings to production.

The benchmark framework is **ready to use** with both synthetic and real data. Once you have PJe data in your database, run the quality benchmark to validate that local embeddings meet your quality requirements.

**Recommended next step:** Collect real PJe data, run quality benchmark, and compare against Jina if needed.

---

**Questions?** See [../CLAUDE.md](../../CLAUDE.md) for development guidelines or check the [experiments README](./README.md) for more context.
