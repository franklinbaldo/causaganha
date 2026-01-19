# Internet Archive Data Lake Architecture

**Purpose**: CausaGanha uses Internet Archive as a free, distributed, permanent data lake for all judicial decision data.

---

## 🎯 Why Internet Archive as Data Lake

### Cost Savings
- **Storage**: $0 (IA is free for public data)
- **Bandwidth**: $0 (IA handles distribution)
- **Alternative cost**: AWS S3 would be ~$1,200/year for 50GB + transfer costs

### Architectural Benefits
- **Distributed**: No single point of failure
- **Permanent**: Survives beyond project lifetime
- **Public**: Anyone can verify and reproduce ratings
- **Auditable**: Complete transparency and data lineage

### Open Data Mission
- Supports transparency goals
- Enables independent research
- Reproducible science
- Democratic access to legal data

---

## 📦 Data Format: Apache Parquet

### Why Parquet over JSON/CSV?
| Format | Size | Query Speed | Compression | Schema | Best For |
|--------|------|-------------|-------------|---------|----------|
| JSON   | 100% | Slow        | Poor        | No      | APIs     |
| CSV    | 50%  | Slow        | Poor        | No      | Excel    |
| Parquet| 10%  | **Fast**    | **Good**    | **Yes** | **Analytics** |

### Parquet Advantages
- **Columnar storage**: Query only needed columns
- **Compression**: 10-20x smaller than JSON
- **Schema enforcement**: Built-in data validation
- **Wide adoption**: Works with DuckDB, Pandas, Spark, BigQuery

---

## 🗂️ Partitioning Strategy

### Goals
1. **Efficient downloads**: Users download only data they need
2. **Query performance**: Fast filtering without full scan
3. **Incremental updates**: Append new data without rewriting
4. **Natural boundaries**: Match common access patterns

### Option 1: By Tribunal Only
```
internet-archive/
├── causaganha-TJRO.parquet
├── causaganha-TJAC.parquet
├── causaganha-TJSP.parquet
└── ...
```

**Pros:**
- Simple structure
- Natural boundary (tribunal = jurisdiction)
- Easy to download per state

**Cons:**
- Large files for TJSP (millions of records)
- Hard to get "recent data only"
- Rewrites entire file on update

**Verdict:** ❌ Poor for large tribunals

---

### Option 2: By Date (Year/Month)
```
internet-archive/
├── causaganha-2024-01.parquet
├── causaganha-2024-02.parquet
├── causaganha-2025-01.parquet
└── ...
```

**Pros:**
- Time-series queries efficient
- Incremental updates natural
- File sizes bounded by month

**Cons:**
- Must download all tribunals to get one tribunal
- Cross-tribunal queries require multiple files
- Doesn't match primary access pattern

**Verdict:** ❌ Poor for tribunal-specific queries

---

### Option 3: By Tribunal + Date (Hierarchical) ⭐ RECOMMENDED
```
internet-archive/
├── causaganha-TJRO-2024-01.parquet
├── causaganha-TJRO-2024-02.parquet
├── causaganha-TJRO-2025-01.parquet
├── causaganha-TJAC-2024-12.parquet
├── causaganha-TJAC-2025-01.parquet
└── ...
```

**Pros:**
- ✅ Download specific tribunal + time range
- ✅ Incremental updates (new file per month)
- ✅ Bounded file sizes (~1-10MB per file)
- ✅ Natural append-only model
- ✅ Supports both access patterns:
  - "All TJRO data" → download all causaganha-TJRO-*.parquet
  - "Recent data" → download all causaganha-*-2025-01.parquet

**Cons:**
- More files to manage (but Internet Archive handles this)
- Slightly more complex naming

**Verdict:** ✅ **RECOMMENDED**

---

### Option 4: Hive-style Partitioning
```
internet-archive/
├── tribunal=TJRO/
│   ├── year=2024/
│   │   ├── month=01/data.parquet
│   │   └── month=02/data.parquet
│   └── year=2025/
│       └── month=01/data.parquet
└── tribunal=TJAC/
    └── year=2025/
        └── month=01/data.parquet
```

**Pros:**
- Standard for big data systems (Spark, Hive)
- Automatic partition pruning in query engines

**Cons:**
- Complex directory structure on IA
- Harder to discover/browse manually
- IA item model doesn't map well to nested directories

**Verdict:** ⚠️ Overkill for this use case

---

## 🏆 Final Recommendation: Option 3

**Naming Convention:**
```
causaganha-{TRIBUNAL}-{YEAR}-{MONTH}.parquet
```

**Examples:**
- `causaganha-TJRO-2025-01.parquet`
- `causaganha-TJSP-2024-12.parquet`

**Metadata (IA Item Description):**
```json
{
  "title": "CausaGanha - TJRO - January 2025",
  "collection": "causaganha",
  "mediatype": "data",
  "subject": ["judicial decisions", "brazil", "TJRO", "2025-01"],
  "description": "Tabulated judicial decision data from Tribunal de Justiça de Rondônia for January 2025. Contains lawyer information, case outcomes, and LLM-extracted decision analysis.",
  "format": "Parquet",
  "coverage": "TJRO",
  "date": "2025-01"
}
```

---

## 📊 Schema Design

### Table: `intimations`
All data in a single denormalized Parquet file for efficient querying.

```sql
CREATE TABLE intimations (
    -- Identifiers
    intimation_id BIGINT,
    numero_processo VARCHAR,
    hash VARCHAR,

    -- Court metadata
    sigla_tribunal VARCHAR,
    nome_orgao VARCHAR,
    data_disponibilizacao DATE,

    -- Decision text (from PJe API)
    texto TEXT,                          -- Full decision text
    tipo_documento VARCHAR,
    nome_classe VARCHAR,

    -- Lawyers (denormalized - can have arrays)
    plaintiff_lawyers STRUCT(
        oab_number VARCHAR,
        oab_state VARCHAR,
        name VARCHAR
    )[],
    defendant_lawyers STRUCT(
        oab_number VARCHAR,
        oab_state VARCHAR,
        name VARCHAR
    )[],

    -- LLM Analysis results
    winner_lawyer_oab VARCHAR,
    winner_lawyer_state VARCHAR,
    loser_lawyer_oab VARCHAR,
    loser_lawyer_state VARCHAR,
    decision_type VARCHAR,               -- SENTENÇA, ACÓRDÃO, etc.
    outcome VARCHAR,                     -- PROCEDENTE, IMPROCEDENTE, etc.
    judge_name VARCHAR,
    decision_reasoning TEXT,
    confidence_score FLOAT,

    -- Ratings (at time of export)
    winner_rating_before FLOAT,
    winner_rating_after FLOAT,
    loser_rating_before FLOAT,
    loser_rating_after FLOAT,

    -- Processing metadata
    analyzed_at TIMESTAMP,
    llm_model VARCHAR,
    pipeline_version VARCHAR,

    -- Partition columns
    year INT,
    month INT
)
PARTITION BY (sigla_tribunal, year, month);
```

**Note**: Parquet supports nested structures (arrays, structs), so we can denormalize lawyers instead of requiring joins.

---

## 🔍 Query Examples

### Example 1: All TJRO decisions in 2025
```python
import duckdb

# Download files
# causaganha-TJRO-2025-01.parquet
# causaganha-TJRO-2025-02.parquet

# Query
con = duckdb.connect()
df = con.execute("""
    SELECT * FROM 'causaganha-TJRO-2025-*.parquet'
    WHERE sigla_tribunal = 'TJRO'
""").df()
```

### Example 2: All January 2025 decisions (any tribunal)
```python
df = con.execute("""
    SELECT * FROM 'causaganha-*-2025-01.parquet'
""").df()
```

### Example 3: Lawyer performance analysis
```python
df = con.execute("""
    SELECT
        winner_lawyer_oab,
        winner_lawyer_state,
        COUNT(*) as wins,
        AVG(confidence_score) as avg_confidence
    FROM 'causaganha-TJSP-*.parquet'
    WHERE year = 2024
    GROUP BY winner_lawyer_oab, winner_lawyer_state
    ORDER BY wins DESC
    LIMIT 100
""").df()
```

---

## 📤 Upload Strategy

### Initial Upload (Backfill)
For each (tribunal, year, month) combination:
1. Query DuckDB for all intimations in that partition
2. Export to Parquet file
3. Upload to IA with metadata
4. Record IA URL in local database

### Incremental Updates (Daily Pipeline)
1. Collect new intimations (current month)
2. Analyze with LLM
3. Update DuckDB
4. At end of month: export current month partition
5. Upload to IA (immutable, append-only)

**Note**: Parquet files are **immutable**. Don't update existing files; create new versions if corrections are needed.

---

## 🔄 Update Strategy for Corrections

### Problem
What if an analysis is wrong and corrected later?

### Solution Options

**Option A: Versioned Files**
```
causaganha-TJRO-2025-01-v1.parquet  # Original
causaganha-TJRO-2025-01-v2.parquet  # Corrected
```

**Option B: Separate Corrections Table**
```
causaganha-TJRO-2025-01.parquet          # Original data
causaganha-TJRO-2025-01-corrections.parquet  # Corrections
```
Query: `SELECT * FROM original LEFT JOIN corrections USING (intimation_id)`

**Option C: Tombstone Pattern**
Include `is_corrected` and `correction_id` columns in schema.

**Recommendation**: **Option B** - Keeps original data immutable while allowing corrections.

---

## 💾 Storage Estimates

### Per Decision
- Raw JSON: ~5KB
- Parquet (compressed): ~500 bytes
- Compression ratio: **10x**

### Per Month (TJRO ~100 decisions/day = 3,000/month)
- Raw: 15 MB
- Parquet: **1.5 MB per file**

### Year 1 (5 tribunals, 12 months)
- Total files: 60 files
- Total storage: ~90 MB
- Cost on IA: **$0**

### Year 2 (10 tribunals, 12 months)
- Total files: 120 files
- Total storage: ~200 MB
- Cost on IA: **$0**

### At Scale (90 tribunals, 5 years)
- Total files: 5,400 files
- Total storage: ~10 GB
- Cost on IA: **$0**
- Cost on AWS S3: **~$300/year + bandwidth**

---

## 🎯 Implementation Checklist

### Phase 1: MVP (Current)
- [ ] Define Parquet schema
- [ ] Implement export from DuckDB to Parquet
- [ ] Implement IA upload with metadata
- [ ] Test with single month (TJRO 2025-01)
- [ ] Verify query performance

### Phase 2: Automation
- [ ] Daily pipeline exports current month
- [ ] End-of-month: finalize and upload
- [ ] Backfill historical data
- [ ] Document query patterns

### Phase 3: Optimization
- [ ] Evaluate compression options (snappy vs gzip)
- [ ] Consider row group size tuning
- [ ] Add statistics to Parquet files
- [ ] Benchmark query performance at scale

---

## 🔧 Tools & Libraries

**Python Libraries:**
- `pyarrow` - Parquet read/write
- `pandas` - Data manipulation
- `duckdb` - Local queries
- `internetarchive` - IA uploads

**Example Code:**
```python
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb

# Export from DuckDB
con = duckdb.connect('causaganha.duckdb')
df = con.execute("""
    SELECT * FROM intimations
    WHERE sigla_tribunal = 'TJRO'
    AND year = 2025
    AND month = 1
""").df()

# Write Parquet
table = pa.Table.from_pandas(df)
pq.write_table(
    table,
    'causaganha-TJRO-2025-01.parquet',
    compression='snappy',
    row_group_size=10000
)

# Upload to IA
import internetarchive as ia
item = ia.get_item('causaganha-TJRO-2025-01')
item.upload('causaganha-TJRO-2025-01.parquet', metadata={
    'title': 'CausaGanha - TJRO - January 2025',
    'collection': 'causaganha',
    'mediatype': 'data',
    'subject': ['judicial-decisions', 'brazil', 'TJRO'],
})
```

---

**Last Updated:** 2025-01-19
**Status:** Architecture design complete, awaiting implementation
**Next Steps:** Implement Parquet export and test with sample data
