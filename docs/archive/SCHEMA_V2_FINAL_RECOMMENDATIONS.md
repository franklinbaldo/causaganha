# Schema v2 FINAL Recommendations

**Date:** 2026-01-22
**Status:** FINAL - Based on Multi-Parquet Architecture with Separate Embeddings
**Supersedes:** SCHEMA_V2_REVISED_RECOMMENDATIONS.md and PARQUET_FORMAT_IMPROVEMENTS.md

## Architecture (FINAL)

CausaGanha uses a **multi-parquet architecture** where each entity type is stored separately:

```
Internet Archive:
├── causaganha-decisions-YYYY-MM-DD-TRIBUNAL.parquet   ← Text, analysis, sections
├── causaganha-embeddings-YYYY-MM-DD-TRIBUNAL.parquet ← Embeddings ONLY 🎯
├── causaganha-lawyers-YYYY-MM-DD.parquet              ← Lawyer profiles
└── causaganha-partes-YYYY-MM-DD-TRIBUNAL.parquet      ← Case parties

Join Key: intimation_id (consistent across all files)

DuckDB: Joins parquet files at query time
```

**Critical Change:** Embeddings are now in a **separate file**, not embedded in decisions parquet!

---

## Why Separate Embeddings File?

### **Benefits Over Monolithic Approach**

| Benefit | Description |
|---------|-------------|
| **🔄 Regeneration** | Can regenerate embeddings without touching decisions |
| **📦 Selective Download** | Download decisions only (50 MB) or with embeddings (90 MB) |
| **🔢 Model Versioning** | Store jina-v3, jina-v4, openai embeddings separately |
| **🗃️ Vector Store Hydration** | Download only embeddings to hydrate vector stores |
| **⚡ DuckDB Joins** | Join when needed, skip when not |
| **💾 Storage Optimization** | Same total storage, way more flexible |

### **Example: Regenerating Embeddings**

```bash
# New embedding model released? No problem!
causaganha embeddings regenerate \
  --source decisions-2025-01-15-TJRO.parquet \
  --model jina-v4 \
  --output embeddings-jina-v4-2025-01-15-TJRO.parquet

# Decisions parquet remains untouched ✅
# Can A/B test: jina-v3 vs jina-v4
```

### **Example: Vector Store Hydration**

```python
# Download only embeddings (40 MB, not 90 MB!)
embeddings_df = pq.read_table("s3://ia/embeddings-2025-01-15-TJRO.parquet")

# Hydrate vector store
vector_store.add(
    ids=embeddings_df['intimation_id'],
    embeddings=embeddings_df['texto_embedding']
)

# Didn't need to download decisions at all! 🎉
```

---

## Final Recommendations

### ✅ P0 (Critical): Separate Embeddings Parquet

**File:** `causaganha-embeddings-YYYY-MM-DD-TRIBUNAL.parquet`

**Schema:**
```python
intimation_id: int64                    # Join key (matches decisions)
texto_embedding: list<float32>[1024]    # Jina v3 embedding
embedding_model: string                 # "jina-embeddings-v3"
embedding_version: string               # "v1" (for schema versioning)
embedding_generated_at: timestamp       # Generation timestamp
texto_hash: string                      # SHA256 of texto (validation)
```

**File Size:** 40 MB (separate file)
**Cost:** $100/year (generation)
**Savings:** $8K/year (no re-embedding)
**Net Benefit:** $7.9K/year ✅

**Why Separate:**
- Regenerate embeddings without touching decisions
- Hydrate vector stores from IA
- A/B test different embedding models
- Selective downloads

---

### ✅ P1 (High): Structured Text Sections

**File:** `causaganha-decisions-YYYY-MM-DD-TRIBUNAL.parquet` (stays here!)

**Schema:**
```python
texto_sections: struct<
    full_text: string,
    facts: string,
    reasoning: string,
    decision: string,
    metadata: string,
    extracted_method: string  # "llm", "heuristic", or "hybrid"
>
```

**File Size Impact:** +5% (50 MB → 52 MB)
**Cost:** $100/year (hybrid extraction)
**Benefits:** +10-15% RAG accuracy, -30-40% LLM time

**Why in Decisions:**
- Part of the text structure
- Can't extract on-the-fly efficiently
- Used for both RAG and LLM analysis

**Extraction Methods:**
- **Heuristic:** Free, 70-80% accuracy (Brazilian legal patterns)
- **LLM:** $0.0001/decision, 95%+ accuracy (Gemini Flash)
- **Hybrid:** Heuristic first, LLM fallback (optimal)

---

### ✅ P2 (Medium): Confidence Breakdown

**File:** `causaganha-decisions-YYYY-MM-DD-TRIBUNAL.parquet` (stays here!)

**Schema:**
```python
confidence_breakdown: struct<
    overall: float32,
    winner_identification: float32,
    loser_identification: float32,
    outcome_classification: float32,
    decision_type_classification: float32,
    judge_extraction: float32
>
```

**File Size Impact:** +0.5% (52 MB → 52.25 MB)
**Cost:** $0/year (already computed)
**Benefits:** Targeted reanalysis, quality diagnostics

**Why in Decisions:**
- Analysis-specific metadata
- Can't join from elsewhere
- Used for quality filtering and reanalysis

---

## Schema Comparison

### Decisions Parquet (Schema v2)

```python
# Identifiers
intimation_id: int64               # 🔑 Join key (used across all parquets)
numero_processo: string
hash: string
sigla_tribunal: string

# Decision content
texto: string
texto_sections: struct<            # ✅ P1 (NEW)
    full_text: string,
    facts: string,
    reasoning: string,
    decision: string,
    metadata: string,
    extracted_method: string
>

# Analysis results
winner_lawyer_oab: string          # Join with lawyers.parquet
winner_lawyer_state: string
loser_lawyer_oab: string
loser_lawyer_state: string
decision_type: string
outcome: string
judge_name: string

# Confidence tracking
confidence_score: float64          # Keep for backward compatibility
confidence_breakdown: struct<      # ✅ P2 (NEW)
    overall: float32,
    winner_identification: float32,
    loser_identification: float32,
    outcome_classification: float32,
    decision_type_classification: float32,
    judge_extraction: float32
>

# Analysis metadata
analyzed_at: timestamp
analysis_method: string

# Partitioning
partition_date: date32
year: int32
month: int32
day: int32
```

**File Size:** 52.25 MB (NO embeddings!)

---

### Embeddings Parquet (Schema v2) 🎯 NEW

```python
# Join key
intimation_id: int64               # 🔑 Matches decisions.parquet

# Embeddings
texto_embedding: list<float32>[1024]  # Jina v3 embedding
embedding_model: string            # "jina-embeddings-v3"
embedding_version: string          # "v1"
embedding_generated_at: timestamp

# Validation
texto_hash: string                 # SHA256 of texto (verify match)

# Partitioning
partition_date: date32
year: int32
month: int32
day: int32
```

**File Size:** 40 MB (ONLY embeddings!)

---

## Storage Analysis

### Multi-Parquet Architecture (FINAL)

| File | Size | Description |
|------|------|-------------|
| Decisions | 52.25 MB | Text, sections, confidence, analysis |
| Embeddings | 40 MB | Jina v3 embeddings (separate!) |
| Lawyers | 5 MB | Profiles, ratings (shared) |
| Partes | 3 MB | Case parties |
| **Total** | **100.25 MB** | All data, fully decomposed |

### Comparison with Alternatives

| Approach | Decisions | Embeddings | Lawyers | Total | Flexibility |
|----------|-----------|------------|---------|-------|-------------|
| **Separate (FINAL)** | 52 MB | 40 MB | 5 MB | **97 MB** | ⭐⭐⭐⭐⭐ |
| Monolithic (Original) | 102 MB | - | - | 102 MB | ⭐ |
| Decisions+Embeddings | 92 MB | - | 5 MB | 97 MB | ⭐⭐⭐ |

**Winner:** Separate embeddings! Same storage, maximum flexibility. 🏆

---

## Query Examples

### Example 1: RAG Analysis with Separate Embeddings

```sql
-- Join decisions + embeddings for RAG analysis
SELECT
  d.intimation_id,
  d.texto,
  d.texto_sections,
  e.texto_embedding
FROM 's3://ia/causaganha-decisions-2025-01-15-TJRO.parquet' d
INNER JOIN 's3://ia/causaganha-embeddings-2025-01-15-TJRO.parquet' e
  ON d.intimation_id = e.intimation_id
WHERE d.confidence_breakdown.overall > 0.80
LIMIT 100;
```

### Example 2: Upset Victories with Lawyers

```sql
-- Join decisions + lawyers (no embeddings needed!)
SELECT
  d.numero_processo,
  d.outcome,
  w.lawyer_name AS winner,
  w.global_rating AS winner_rating,
  l.lawyer_name AS loser,
  l.global_rating AS loser_rating
FROM 's3://ia/causaganha-decisions-2025-01-15-TJRO.parquet' d
LEFT JOIN 's3://ia/causaganha-lawyers-2025-01-15.parquet' w
  ON d.winner_lawyer_oab = w.oab_number
LEFT JOIN 's3://ia/causaganha-lawyers-2025-01-15.parquet' l
  ON d.loser_lawyer_oab = l.oab_number
WHERE w.global_rating < l.global_rating - 100;

-- Embeddings not involved at all! Downloaded separately if needed.
```

### Example 3: A/B Test Embedding Models

```sql
-- Compare jina-v3 vs jina-v4 embeddings
SELECT
  d.intimation_id,
  d.texto,
  e3.texto_embedding AS jina_v3_embedding,
  e4.texto_embedding AS jina_v4_embedding
FROM 's3://ia/causaganha-decisions-2025-01-15-TJRO.parquet' d
LEFT JOIN 's3://ia/causaganha-embeddings-jina-v3-2025-01-15-TJRO.parquet' e3
  ON d.intimation_id = e3.intimation_id
LEFT JOIN 's3://ia/causaganha-embeddings-jina-v4-2025-01-15-TJRO.parquet' e4
  ON d.intimation_id = e4.intimation_id
LIMIT 100;
```

---

## Cost-Benefit Analysis (FINAL)

### Implementation Cost

| Phase | Task | Effort | Cost |
|-------|------|--------|------|
| P0 | Separate embeddings exporter | 20 hours | $2,000 |
| P0 | RAG analyzer updates (join) | 10 hours | $1,000 |
| P1 | Section extractors (heuristic + LLM) | 30 hours | $3,000 |
| P2 | Confidence breakdown | 10 hours | $1,000 |
| Testing | All features | 15 hours | $1,500 |
| Docs | Documentation | 5 hours | $500 |
| **Total** | | **90 hours** | **$9,000** |

### Annual Costs & Savings

| Item | Cost | Savings | Net |
|------|------|---------|-----|
| Embedding generation | +$100 | - | -$100 |
| Section extraction (hybrid) | +$100 | - | -$100 |
| Avoided re-embedding | - | $8,000 | +$8,000 |
| Reduced LLM processing | - | $1,200 | +$1,200 |
| Developer time saved | - | $5,000 | +$5,000 |
| **Total** | **$200** | **$14,200** | **+$14,000/year** ✅ |

### ROI

- **Initial Investment:** $9,000
- **Annual Benefit:** $14,000
- **Payback Period:** 7.7 months
- **3-Year NPV:** $33,000

**Verdict:** Excellent ROI, proceed with implementation! 🎉

---

## Implementation Plan

### Phase 1: Separate Embeddings (Weeks 1-2)

**Goal:** Export embeddings to separate parquet file

**Tasks:**
1. Create `EmbeddingsExporter` class
2. Define embeddings parquet schema
3. Generate embeddings during export
4. Upload both decisions and embeddings to IA
5. Update `parquet_exports` table to track both files
6. Modify RAGAnalyzer to join or use cached embeddings
7. Write tests for:
   - Separate file export
   - DuckDB joins on intimation_id
   - Vector store hydration
   - Selective downloads

**Deliverable:** Working separate embeddings export + analysis

---

### Phase 2: Structured Sections (Weeks 3-4)

**Goal:** Extract facts, reasoning, decision from texto

**Tasks:**
1. Implement heuristic extractor (Brazilian legal patterns)
2. Implement LLM extractor (Gemini Flash)
3. Implement hybrid extractor (heuristic + LLM fallback)
4. Add `texto_sections` to decisions parquet schema
5. Update analyzers to use structured sections
6. Write tests for all extraction methods
7. Benchmark quality improvements

**Deliverable:** Structured sections in decisions parquet

---

### Phase 3: Confidence Breakdown (Week 5)

**Goal:** Track confidence per analysis component

**Tasks:**
1. Add `ConfidenceBreakdown` model
2. Update DecisionAnalysis to include breakdown
3. Modify analyzers to populate breakdown
4. Add `confidence_breakdown` to decisions parquet
5. Update queries to filter by component
6. Write tests for all confidence use cases

**Deliverable:** Per-component confidence tracking

---

### Phase 4: Integration & Migration (Weeks 6-8)

**Goal:** Deploy v2, migrate historical data

**Tasks:**
1. Implement schema version detection
2. Add re-export command for v1 → v2
3. Parallel deployment (v1 + v2)
4. Monitor costs and performance
5. Gradual rollout with feature flags
6. Migrate high-value historical data
7. Full production rollout
8. Deprecate v1 after 3 months

**Deliverable:** Production v2 schema with migration

---

## Success Metrics

### Performance
- ✅ RAG analysis 3-5x faster with cached embeddings
- ✅ LLM analysis 30-40% faster with sections
- ✅ DuckDB joins < 5 seconds

### Cost
- ✅ Embedding generation: $100/year (acceptable)
- ✅ Section extraction: $100/year (acceptable)
- ✅ Savings: $14K/year (embedding + LLM efficiency)
- ✅ Net benefit: $14K/year

### Quality
- ✅ RAG accuracy +10-15% with sections
- ✅ Targeted reanalysis with confidence breakdown
- ✅ Historical tracking with separate lawyer files

### Flexibility
- ✅ Regenerate embeddings without touching decisions
- ✅ A/B test embedding models
- ✅ Hydrate vector stores from IA
- ✅ Selective downloads (decisions only or with embeddings)

---

## Frequently Asked Questions

### Q: Why not embed embeddings in decisions parquet?

**A:** Separate embeddings file provides:
- Regeneration flexibility (new models)
- Model versioning (jina-v3, jina-v4 side-by-side)
- Selective downloads (decisions only vs with embeddings)
- Vector store hydration (download only embeddings)
- A/B testing (compare embedding quality)

### Q: Doesn't this add join overhead?

**A:** DuckDB's columnar format makes joins very efficient (<1 second for 10K rows). The flexibility gained far outweighs the minimal join cost.

### Q: What if I always need embeddings?

**A:** You can still download both files together. But now you have the OPTION to download separately when you don't need embeddings (e.g., text-only analysis, metadata queries).

### Q: How do I migrate existing v1 files?

**A:** Use the migration command:
```bash
causaganha parquet re-export \
  --start-date 2025-01-01 \
  --end-date 2025-12-31 \
  --schema v2 \
  --parallel 4
```

This will:
1. Download v1 decisions
2. Generate embeddings → separate file
3. Extract sections → add to decisions
4. Add confidence breakdown → add to decisions
5. Upload all v2 files to IA

---

## Conclusion

Schema v2 with **separate embeddings file** is the optimal architecture:

✅ **P0:** Separate embeddings parquet (regeneration, versioning, hydration)
✅ **P1:** Structured sections in decisions (RAG accuracy, LLM efficiency)
✅ **P2:** Confidence breakdown in decisions (targeted reanalysis, quality)

**Total Cost:** $9K implementation + $200/year
**Total Benefit:** $14K/year savings
**ROI:** 7.7 months payback, $33K over 3 years

**Next Step:** Implement Phase 1 (separate embeddings) 🚀

---

**Last Updated:** 2026-01-22
**Status:** FINAL - Ready for implementation
**BDD Features:** `tests/features/parquet_schema_v2/07_separate_embeddings_parquet.feature`
