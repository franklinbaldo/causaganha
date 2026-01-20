# Architecture Clarification: texto + Parquet Data Lake

**Date:** 2025-01-19
**Status:** Architecture finalized based on PJe API capabilities

---

## 🎯 Key Insight

**The `texto` field in PJe API contains the full decision text**, eliminating the need for PDF downloads during normal pipeline operation.

---

## ✅ Corrected Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  PJe Communications API                                       │
│  Returns: intimations with texto field (full decision text)  │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  COLLECT            │
                  │  - Intimations      │
                  │  - texto field      │
                  │  - Lawyer info (OAB)│
                  │  - Case metadata    │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  DuckDB (Local)     │
                  │  Working database   │
                  │  Last 6 months      │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  ANALYZE            │
                  │  Gemini LLM reads   │
                  │  texto field        │
                  │  → Extract outcomes │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  SCORE              │
                  │  OpenSkill ratings  │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  EXPORT             │
                  │  DuckDB → Parquet   │
                  │  Partition by       │
                  │  tribunal + date    │
                  └──────────┬──────────┘
                             │
                             ▼
         ┌───────────────────────────────────────────┐
         │  Internet Archive (Data Lake)             │
         │  - FREE distributed storage                │
         │  - Parquet files (10x compression)        │
         │  - Public download & verification         │
         │  - causaganha-TJRO-2025-01.parquet        │
         └───────────────────────────────────────────┘
```

---

## 📦 What the PJe API Provides

### ✅ Available Directly from API
- **Case metadata**: numero_processo, tribunal, dates, case class
- **Lawyer information**: OAB numbers, names, states (via `destinatarioadvogados`)
- **Party information**: Names, plaintiff/defendant pole (via `destinatarios`)
- **Decision text**: **`texto` field contains full decision**
- **PDF links**: URL to original PDF (for reference, not analysis)

### ❌ NOT Available (Requires LLM Analysis)
- **Winner/loser determination**: Which lawyer won?
- **Decision outcome**: PROCEDENTE, IMPROCEDENTE, etc.
- **Decision type**: SENTENÇA, ACÓRDÃO, etc.
- **Judge name**: Not in API metadata
- **Decision reasoning**: Summary of legal basis

---

## 🔍 Why LLM Analysis is Still Required

The PJe API is a **communications/notification system**, not a legal data API. It tells you:
- ✅ "Document X was published"
- ✅ "Lawyers A and B were notified"
- ✅ "Here's the decision text (in `texto` field)"

But it does NOT tell you:
- ❌ "Lawyer A won and Lawyer B lost"
- ❌ "The outcome was PROCEDENTE"
- ❌ "The judge's reasoning was X"

**Therefore**: LLM analysis of the `texto` field is necessary to extract legal outcomes.

---

## 💾 Internet Archive as Data Lake

### Dual Purpose
1. **Free Distributed Storage** ($0 cost vs. $1,500+/year on AWS)
2. **Public Verification** (anyone can download and verify ratings)

### Data Format: Apache Parquet
- **Columnar storage**: Query only needed columns
- **10x compression**: 5KB JSON → 500 bytes Parquet
- **Schema enforcement**: Built-in validation
- **Fast queries**: DuckDB, Pandas, Spark compatible

### Partitioning Strategy
**Format:** `causaganha-{TRIBUNAL}-{YEAR}-{MONTH}.parquet`

**Examples:**
- `causaganha-TJRO-2025-01.parquet` (1.5 MB, 3,000 decisions)
- `causaganha-TJSP-2025-01.parquet` (50 MB, 150,000 decisions)

**Benefits:**
- Download only needed tribunals/dates
- Incremental updates (new file per month)
- Bounded file sizes
- Natural append-only model

---

## 🔄 Data Flow

### Pipeline Execution (Daily)
1. **Collect** (5 min): PJe API → DuckDB (with `texto` field)
2. **Analyze** (2 hr): Gemini LLM analyzes `texto` → Extract outcomes
3. **Score** (5 min): OpenSkill calculates ratings
4. **Export** (10 min): DuckDB → Parquet (monthly partitions)
5. **Archive** (30 min): Upload Parquet to Internet Archive

**Total: ~3 hours/day for 500 decisions**

### Monthly Export
At end of each month:
1. Query DuckDB for all (tribunal, month) combinations
2. Export each to Parquet file
3. Upload to Internet Archive
4. Purge old data from DuckDB (keep last 6 months)

---

## 💰 Cost Comparison

| Component | Old Assumption | Actual Cost | Annual Savings |
|-----------|---------------|-------------|----------------|
| Storage | AWS S3: $100-1,500/mo | IA: $0 | $1,200-18,000 |
| Database | PostgreSQL: $25-200/mo | DuckDB: $0 | $300-2,400 |
| PDF Processing | High complexity | texto field | N/A |
| **Total Savings** | | | **$1,500-20,400/year** |

---

## 📊 Storage Estimates

| Phase | Decisions | DuckDB (Working) | IA Parquet | AWS S3 Cost | Actual Cost |
|-------|-----------|------------------|------------|-------------|-------------|
| MVP | 50K | 500 MB | 5 MB | $15/mo | $0 |
| Year 1 | 500K | 5 GB | 50 MB | $100/mo | $0 |
| Year 2 | 2M | 20 GB | 200 MB | $300/mo | $0 |
| Year 5 | 10M | 100 GB | 1 GB | $1,500/mo | $0 |

---

## 🎯 What Changed in Documentation

### Updated Documents
1. **PRODUCT_VISION.md** - Updated core loop, emphasized data lake architecture
2. **MVP_SCOPE.md** - Changed "PDF download" to "texto analysis", updated archival to Parquet export
3. **ROADMAP.md** - Clarified technology stack
4. **TECHNICAL_REQUIREMENTS.md** - Updated storage, costs, and infrastructure
5. **DATA_LAKE_ARCHITECTURE.md** (NEW) - Complete Parquet partitioning strategy

### Still TODO
- Update BDD feature: `04_document_archival.feature` → Parquet export scenarios
- Update BDD feature: `12_transparency.feature` → Data lake verification scenarios
- Remove PDF-specific scenarios that are no longer applicable

---

## 🔑 Key Takeaways

1. ✅ **texto field is sufficient** - No PDF downloads needed for analysis
2. ✅ **LLM still required** - PJe API doesn't provide legal outcomes
3. ✅ **Internet Archive is primary database** - Free, distributed, permanent
4. ✅ **Parquet format** - 10x compression, fast queries
5. ✅ **DuckDB is staging** - Working database, not permanent storage
6. ✅ **Huge cost savings** - $0 vs. $1,500-20,000/year

---

## 📚 Related Documentation

- [DATA_LAKE_ARCHITECTURE.md](./DATA_LAKE_ARCHITECTURE.md) - Detailed Parquet strategy
- [PRODUCT_VISION.md](./PRODUCT_VISION.md) - Updated product vision
- [MVP_SCOPE.md](./MVP_SCOPE.md) - Updated MVP scope
- [TECHNICAL_REQUIREMENTS.md](./TECHNICAL_REQUIREMENTS.md) - Updated technical specs

---

**Last Updated:** 2025-01-19
**Architectural Review:** Complete
**Implementation Status:** Ready for development
