# Parquet Schema v2 BDD Features

**Status:** Specification (Not Yet Implemented)
**Target Release:** v2.1.0

## Overview

This directory contains BDD (Behavior-Driven Development) feature specifications for CausaGanha's Parquet Schema v2 enhancements. These features describe the desired behavior for improved parquet export, analysis, and querying capabilities.

## Architecture Context

CausaGanha uses a **multi-parquet architecture** with separate files for different entities:

```
Internet Archive Storage:
├── causaganha-decisions-YYYY-MM-DD-TRIBUNAL.parquet  ← Decision text, analysis, embeddings
├── causaganha-lawyers-YYYY-MM-DD.parquet             ← Lawyer profiles and ratings
└── causaganha-partes-YYYY-MM-DD-TRIBUNAL.parquet     ← Case parties information

DuckDB Query Engine:
└── Joins parquet files at query time (no duplication needed!)
```

**Key Insight:** Lawyer data is already in separate parquet files, so we DON'T need to embed it in decisions parquet. DuckDB handles joins efficiently at query time.

## Feature Files

### Priority 0 (Critical)

#### `01_P0_precomputed_embeddings.feature`
**Pre-computed Embeddings** - Store Jina v3 embeddings in decisions parquet

- **Problem:** RAG analysis re-embeds texto every time (slow, expensive)
- **Solution:** Compute embeddings once during export, cache in parquet
- **Benefits:**
  - 3-5x faster RAG analysis
  - $8K/year savings (1M decisions)
  - Enables similarity search directly on parquet
  - Offline analysis without embedding API
- **File Size Impact:** +80% (50MB → 90MB)
- **ROI:** 6 months payback

**Scenarios:**
- Export parquet with pre-computed embeddings
- RAG analysis using cached embeddings from parquet
- Performance comparison - cached vs generated embeddings
- Validate embedding quality in parquet
- Schema v1 backward compatibility
- Re-export v1 files to v2 with embeddings
- Track embedding generation costs
- Enable similarity search on parquet
- Distributed analysis without embedding API

---

### Priority 1 (High)

#### `02_P1_structured_text_sections.feature`
**Structured Text Sections** - Split decision text into facts, reasoning, decision

- **Problem:** Flat texto field makes RAG noisy and LLM processing slow
- **Solution:** Extract structured sections (facts, reasoning, decision, metadata)
- **Methods:**
  - **Heuristic:** Free, fast, 70-80% accuracy (regex patterns)
  - **LLM:** $0.0001/decision, slower, 95%+ accuracy
  - **Hybrid:** Heuristic first, LLM fallback (optimal)
- **Benefits:**
  - +10-15% RAG accuracy (cleaner embeddings)
  - -30-40% LLM processing time (focus on relevant sections)
  - Section-specific embeddings (search only in reasoning)
  - Better confidence granularity
- **File Size Impact:** +5-10%
- **Cost:** $100/year (hybrid mode, 1M decisions)

**Scenarios:**
- Export with LLM-extracted sections
- Export with heuristic-extracted sections
- Hybrid extraction (heuristic + LLM fallback)
- Validate section extraction quality
- RAG analysis using structured sections
- LLM analysis using specific sections
- Section-specific embeddings
- Brazilian legal pattern recognition
- Edge case handling
- Backward compatibility with v1
- Quality metrics tracking

---

### Priority 2 (Medium)

#### `03_P2_lawyer_enrichment.feature`
**Lawyer Enrichment** - ~~Embed lawyer profiles in decisions parquet~~

**⚠️ REVISED: NOT NEEDED for multi-parquet architecture!**

Since lawyers are already exported to separate parquet files, we should:
- ✅ Keep using separate lawyers parquet
- ✅ Join at query time with DuckDB
- ❌ Don't duplicate lawyer data in decisions parquet

**Benefits of Separate Files:**
- 49% storage savings (no duplication)
- Flexible updates (change ratings without touching decisions)
- Historical snapshots (export lawyers parquet daily)
- Efficient DuckDB joins (columnar format)

**This feature file is kept for reference but implementation is NOT recommended.**

---

#### `04_P2_confidence_breakdown.feature`
**Confidence Breakdown** - Per-component confidence scores

- **Problem:** Single confidence_score doesn't show which part of analysis is uncertain
- **Solution:** Track confidence per component (winner_id, loser_id, outcome, decision_type, judge_extraction)
- **Benefits:**
  - Targeted reanalysis (only reanalyze weak components)
  - Quality diagnostics (identify weakest components)
  - A/B testing (compare models by component)
  - Better filtering (high confidence in winner but low in judge? fine!)
  - Training data curation (select high-confidence examples)
- **File Size Impact:** +0.5% (negligible)
- **ETL Impact:** Minimal (already computed internally)

**Scenarios:**
- Export with confidence breakdown
- RAG analysis populates breakdown
- LLM analysis populates breakdown
- Targeted reanalysis using component confidence
- Quality diagnostics across dataset
- A/B testing model versions
- Filter high-quality analyses
- Correlation between confidence and accuracy
- Hybrid decision tracking
- Component-specific thresholds
- Training data curation
- Backward compatibility
- Real-time monitoring

---

### Integration

#### `05_schema_v2_integration.feature`
**Schema v2 Integration and Migration**

Full deployment workflow including:
- Schema version detection and validation
- Parallel v1/v2 deployment for validation
- Historical data migration (v1 → v2)
- Batch migration with parallelization
- Mixed v1/v2 analysis workflows
- File size comparisons
- Cost-benefit ROI calculations
- DuckDB query performance
- Versioning and metadata
- Rollback procedures
- Analytics and reporting
- Feature flags for gradual rollout

#### `06_multi_parquet_architecture.feature`
**Multi-Parquet Architecture with DuckDB Joins** ⭐ NEW

Proper architecture specification:
- Decisions parquet contains: text, embeddings, sections, confidence, analysis (NOT lawyer data)
- Lawyers parquet contains: profiles, ratings, statistics (separate file)
- Partes parquet contains: case parties (separate file)
- DuckDB joins parquets at query time
- Storage efficiency (49% savings vs monolithic)
- Historical snapshots (daily lawyer exports)
- Query patterns and optimization
- Partitioning strategies

---

## Revised Schema v2 Recommendations

Based on the multi-parquet architecture:

### ✅ RECOMMENDED (Implement These)

| Priority | Feature | Reason | File Size | Cost/Year |
|----------|---------|--------|-----------|-----------|
| **P0** | Pre-computed Embeddings | Can't compute on-the-fly efficiently | +80% | $100 |
| **P1** | Structured Text Sections | Can't extract on-the-fly efficiently | +10% | $100 |
| **P2** | Confidence Breakdown | Analysis-specific, can't join from elsewhere | +0.5% | $0 |

**Total File Size Increase:** ~90% (50MB → 95MB per file)
**Total Cost:** $200/year
**Total Savings:** $14K/year (embedding reuse + LLM efficiency)
**Net Benefit:** $13.8K/year 🎉

### ❌ NOT RECOMMENDED (Don't Implement)

| Feature | Reason |
|---------|--------|
| Lawyer Enrichment | Already in separate lawyers parquet, join at query time with DuckDB |
| Partes Details | Already in separate partes parquet |
| PDF Content | 100x file size increase, not practical |

---

## Running These Tests

**Note:** These are specifications, not yet implemented. To implement:

1. **Implement the features** in `src/causaganha/v2/`
2. **Write step definitions** in `tests/step_defs/parquet_schema_v2/`
3. **Run tests:**
   ```bash
   # Run all schema v2 tests
   uv run pytest tests/features/parquet_schema_v2/

   # Run specific priority
   uv run pytest tests/features/parquet_schema_v2/01_P0_*.feature

   # Run specific scenario
   uv run pytest tests/features/parquet_schema_v2/01_P0_*.feature -k "cached embeddings"
   ```

---

## Implementation Order

### Phase 1: P0 - Embeddings (Week 1-2)
1. Add embedding generation to ParquetExporter
2. Update schema to include texto_embedding, embedding_model, embedding_generated_at
3. Modify RAGAnalyzer to use cached embeddings
4. Add tests for embedding caching
5. Deploy and validate

### Phase 2: P1 - Sections (Week 3-4)
1. Implement heuristic section extractor (regex patterns for Brazilian legal docs)
2. Implement LLM section extractor (Gemini Flash)
3. Implement hybrid extractor (heuristic + LLM fallback)
4. Add texto_sections struct to parquet schema
5. Update analyzers to use structured sections
6. Add tests for section extraction
7. Deploy and validate

### Phase 3: P2 - Confidence (Week 5)
1. Add ConfidenceBreakdown model
2. Update DecisionAnalysis to include breakdown
3. Modify analyzers to populate breakdown
4. Add confidence_breakdown to parquet schema
5. Update queries to use component-specific filtering
6. Add tests for confidence breakdown
7. Deploy and validate

### Phase 4: Integration & Migration (Week 6-8)
1. Implement schema version detection
2. Add re-export command for v1 → v2 migration
3. Parallel deployment (v1 + v2)
4. Monitoring and analytics
5. Full production rollout
6. Deprecate v1 (after 3 months)

---

## Success Metrics

### Performance
- RAG analysis 3-5x faster with cached embeddings ✅
- LLM analysis 30-40% faster with structured sections ✅
- Query time < 5 seconds for complex DuckDB joins ✅

### Cost
- Embedding API cost: $100/year (acceptable) ✅
- Section extraction cost: $100/year (acceptable) ✅
- Savings: $14K/year (embedding reuse + LLM efficiency) ✅
- Net benefit: $13.8K/year ✅

### Quality
- RAG accuracy +10-15% with structured sections ✅
- Targeted reanalysis using confidence breakdown ✅
- Historical tracking with daily lawyer snapshots ✅

### Storage
- File size increase: ~90% (50MB → 95MB) - acceptable for IA ✅
- Multi-parquet saves 49% vs monolithic approach ✅

---

## Related Documentation

- [Parquet Format Improvements](../../../docs/PARQUET_FORMAT_IMPROVEMENTS.md) - Detailed analysis
- [Parquet Analysis Adaptation Plan](../../../docs/plans/parquet-analysis-adaptation.md) - Implementation plan
- [Texto vs PDF Clarification](../../../docs/TEXTO_VS_PDF_CLARIFICATION.md) - Architecture decisions
- [Lawyer Enrichment Explained](../../../docs/LAWYER_ENRICHMENT_EXPLAINED.md) - Why NOT needed with multi-parquet

---

## Questions?

See the main project documentation in `/docs/` or ask the team in the project repository.

**Last Updated:** 2026-01-22
**Status:** Specification (awaiting implementation)
