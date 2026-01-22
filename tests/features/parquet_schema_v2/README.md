# Parquet Schema v2 BDD Features

**Status:** Specification (Not Yet Implemented)
**Target Release:** v2.1.0

## Overview

This directory contains BDD (Behavior-Driven Development) feature specifications for CausaGanha's Parquet Schema v2 enhancements. These features describe the desired behavior for improved parquet export, analysis, and querying capabilities.

## Architecture Context

CausaGanha uses a **multi-parquet architecture** with separate files for different entities:

```
Internet Archive Storage:
├── causaganha-decisions-YYYY-MM-DD-TRIBUNAL.parquet   ← Decision text, analysis (NO embeddings!)
├── causaganha-embeddings-YYYY-MM-DD-TRIBUNAL.parquet ← Embeddings ONLY! 🎯 NEW
├── causaganha-lawyers-YYYY-MM-DD.parquet              ← Lawyer profiles and ratings
└── causaganha-partes-YYYY-MM-DD-TRIBUNAL.parquet      ← Case parties information

DuckDB Query Engine:
└── Joins parquet files at query time (no duplication needed!)
```

**Key Insights:**
1. **Embeddings are separate:** Stored in their own parquet file with `intimation_id` as join key
2. **Lawyer data is separate:** Already in lawyers parquet, no need to duplicate
3. **DuckDB joins efficiently:** Columnar format enables fast joins at query time
4. **Selective downloads:** Download only what you need (decisions, embeddings, or both)

## Feature Files

### Priority 0 (Critical)

#### `01_P0_precomputed_embeddings.feature` ⚠️ DEPRECATED
**Pre-computed Embeddings in Decisions Parquet** - Original approach (NOT recommended)

**Status:** SUPERSEDED by `07_separate_embeddings_parquet.feature`

This feature file describes embedding embeddings IN decisions parquet, which is NOT the correct architecture. See `07_separate_embeddings_parquet.feature` for the proper approach (separate embeddings file).

---

#### `07_separate_embeddings_parquet.feature` ✅ RECOMMENDED (NEW)
**Separate Embeddings Parquet** - Store embeddings in dedicated parquet file

- **Problem:** RAG analysis re-embeds texto every time (slow, expensive)
- **Solution:** Export embeddings to **separate parquet file** with `intimation_id` as join key
- **Architecture:**
  ```
  causaganha-decisions-2025-01-15-TJRO.parquet   (50 MB - NO embeddings)
  causaganha-embeddings-2025-01-15-TJRO.parquet  (40 MB - ONLY embeddings)
  ```
- **Benefits:**
  - ✅ 3-5x faster RAG analysis (cached embeddings)
  - ✅ $8K/year savings (1M decisions)
  - ✅ Hydrate vector stores directly from IA
  - ✅ Regenerate embeddings without touching decisions
  - ✅ Version embedding models independently
  - ✅ Selective downloads (decisions only or with embeddings)
  - ✅ A/B test different embedding models
- **File Size:** Separate 40 MB file (same total storage, more flexibility!)
- **ROI:** 6 months payback

**Scenarios (16 total):**
- Export embeddings to separate parquet file
- Embeddings and decisions share the same join key
- Embeddings parquet schema definition
- Hydrate vector store from IA embeddings
- RAG analysis using separate embeddings
- Regenerate embeddings without touching decisions
- Store multiple embedding model versions
- Selective download (with/without embeddings)
- DuckDB query joining decisions + embeddings
- Validate embeddings match decisions (texto_hash)
- Storage efficiency comparison
- Export workflow with separate files
- Cost tracking for embeddings
- Handle missing embeddings gracefully
- Incremental embedding generation

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

## Revised Schema v2 Recommendations (FINAL)

Based on the **multi-parquet architecture with separate embeddings file**:

### ✅ RECOMMENDED (Implement These)

| Priority | Feature | Location | Reason | File Size |
|----------|---------|----------|--------|-----------|
| **P0** | Pre-computed Embeddings | **Separate File** 🎯 | Can't compute on-the-fly, enables vector store hydration | 40 MB (separate) |
| **P1** | Structured Text Sections | Decisions Parquet | Part of text structure, can't extract on-the-fly | +5% (52 MB) |
| **P2** | Confidence Breakdown | Decisions Parquet | Analysis-specific, can't join from elsewhere | +0.5% (52.25 MB) |

**Decisions Parquet:** 52.25 MB (text + sections + confidence, NO embeddings!)
**Embeddings Parquet:** 40 MB (ONLY embeddings, separate file)
**Total Storage:** 92.25 MB (same as monolithic, but WAY more flexible!)

**Annual Cost:** $200/year (embedding + section generation)
**Annual Savings:** $14K/year (embedding reuse + LLM efficiency)
**Net Benefit:** $13.8K/year 🎉

### ❌ NOT RECOMMENDED (Don't Implement in Decisions Parquet)

| Feature | Reason |
|---------|--------|
| ~~Embeddings in Decisions~~ | Put in **separate embeddings parquet** instead! |
| Lawyer Enrichment | Already in separate lawyers parquet, join at query time |
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

### Phase 1: P0 - Separate Embeddings File (Week 1-2) 🎯 UPDATED
1. Create EmbeddingsExporter class (separate from ParquetExporter)
2. Design embeddings parquet schema: intimation_id, texto_embedding, embedding_model, texto_hash
3. Export embeddings to **separate file**: `causaganha-embeddings-YYYY-MM-DD-TRIBUNAL.parquet`
4. Upload both decisions and embeddings files to Internet Archive
5. Modify RAGAnalyzer to join decisions + embeddings or use cached embeddings
6. Add tests for:
   - Separate file export
   - DuckDB joins on intimation_id
   - Vector store hydration from IA
   - Selective download (with/without embeddings)
7. Deploy and validate

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
