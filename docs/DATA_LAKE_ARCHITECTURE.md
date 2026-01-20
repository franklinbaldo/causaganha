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

### Option 2: By Date Only - Daily, All Tribunals
```
internet-archive/
├── causaganha-2025-01-01.parquet  # All tribunals, Jan 1 (~135 MB)
├── causaganha-2025-01-02.parquet  # All tribunals, Jan 2 (~135 MB)
├── causaganha-2025-01-03.parquet  # All tribunals, Jan 3 (~135 MB)
└── ...
```

**Pros:**
- Daily incremental exports (no waiting for month end)
- Manageable file sizes (~135-150 MB per day)
- Only 365 files/year
- Natural append-only model
- Time-series queries efficient

**Cons:**
- ❌ Must download all tribunals to get one tribunal's data
- ❌ Larger individual files than hierarchical approach
- ❌ Bandwidth waste if user only needs specific tribunals

**Verdict:** ⚠️ **Good for time-series analysis, but not optimal for selective tribunal downloads**

---

### Option 3: By Date + Tribunal (Hierarchical) ⭐ RECOMMENDED
```
internet-archive/
├── causaganha-2025-01-01-TJRO.parquet  # TJRO Jan 1 (~1.5 MB)
├── causaganha-2025-01-01-TJSP.parquet  # TJSP Jan 1 (~25 MB)
├── causaganha-2025-01-01-TJRJ.parquet  # TJRJ Jan 1 (~15 MB)
├── causaganha-2025-01-02-TJRO.parquet  # TJRO Jan 2
├── causaganha-2025-01-02-TJSP.parquet  # TJSP Jan 2
└── ...
```

**Pros:**
- ✅ Selective downloads by tribunal (download only TJRO files)
- ✅ Selective downloads by date range (download only Jan 1-15)
- ✅ Manageable file sizes (1-50 MB per file, tribunal-dependent)
- ✅ Daily incremental exports (no waiting for month end)
- ✅ Supports both access patterns: by tribunal AND by date
- ✅ Natural append-only model

**Cons:**
- More files to manage (32,850 files/year = 90 tribunals × 365 days)
- But Internet Archive handles this easily

**Why This Works Best:**
- **High Volume**: 270K-450K decisions/day across 90 tribunals
- **File Count**: 32,850 files/year (manageable for IA)
- **Selective Access**: Download only TJRO → 365 files × 1.5 MB = ~547 MB/year
- **Full Access**: Download all → ~49 GB/year (same as Option 2)

**Verdict:** ✅ **RECOMMENDED for flexibility and selective downloads**

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

## 🏆 Final Recommendation: Option 3 (Hierarchical: Date + Tribunal)

**Naming Convention:**
```
causaganha-{YEAR}-{MONTH}-{DAY}-{TRIBUNAL}.parquet
```

**Examples:**
- `causaganha-2025-01-15-TJRO.parquet` (TJRO decisions for Jan 15, 2025)
- `causaganha-2025-01-15-TJSP.parquet` (TJSP decisions for Jan 15, 2025)
- `causaganha-2025-01-16-TJRO.parquet` (TJRO decisions for Jan 16, 2025)

**File Characteristics:**
- **Size**: 1-50 MB per file (tribunal-dependent volume)
- **Rows**: Varies by tribunal (TJRO ~3K/day, TJSP ~50K/day)
- **Compression**: 10:1 ratio (consistent across all files)
- **Frequency**: Daily exports (~90 files/day, one per tribunal)
- **Total files/year**: 32,850 (90 tribunals × 365 days)

**Metadata (IA Item Description):**
```json
{
  "title": "CausaGanha - TJRO - 2025-01-15",
  "collection": "causaganha",
  "mediatype": "data",
  "subject": ["judicial decisions", "brazil", "TJRO", "2025-01-15"],
  "description": "Daily judicial decision data from TJRO (Tribunal de Justiça de Rondônia) for January 15, 2025. Contains lawyer information, case outcomes, and LLM-extracted decision analysis. ~3,000 decisions.",
  "format": "Parquet",
  "coverage": "TJRO (Tribunal de Justiça de Rondônia)",
  "date": "2025-01-15"
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
    partition_date DATE,                  -- Date of the partition (for filtering)
    year INT,
    month INT,
    day INT
)
PARTITION BY (partition_date);
```

**Note**: Parquet supports nested structures (arrays, structs), so we can denormalize lawyers instead of requiring joins.

---

## 🔍 Query Examples

### Example 1: All TJRO decisions in January 2025 (selective download)
```python
import duckdb

# Download only TJRO files for January (31 files × 1.5 MB = ~47 MB)
# causaganha-2025-01-01-TJRO.parquet
# causaganha-2025-01-02-TJRO.parquet
# ...
# causaganha-2025-01-31-TJRO.parquet

# Query all TJRO data
con = duckdb.connect()
df = con.execute("""
    SELECT * FROM 'causaganha-2025-01-*-TJRO.parquet'
""").df()

# Result: ~90K decisions from TJRO in January (3K/day × 30 days)
# Downloaded: ONLY 47 MB (not 4.2 GB!)
```

### Example 2: All decisions on a specific date (all tribunals)
```python
# Download all tribunal files for Jan 15 (90 files × ~1.5 MB avg = ~135 MB)
# causaganha-2025-01-15-*.parquet

df = con.execute("""
    SELECT * FROM 'causaganha-2025-01-15-*.parquet'
""").df()

# Result: ~270K decisions across all 90 tribunals on Jan 15
```

### Example 3: Lawyer performance analysis (TJSP only, Q1 2025)
```python
# Download only TJSP files for Q1 (90 days × 25 MB = ~2.25 GB)
# causaganha-2025-01-*-TJSP.parquet
# causaganha-2025-02-*-TJSP.parquet
# causaganha-2025-03-*-TJSP.parquet

df = con.execute("""
    SELECT
        winner_lawyer_oab,
        winner_lawyer_state,
        COUNT(*) as wins,
        AVG(confidence_score) as avg_confidence
    FROM 'causaganha-2025-*-*-TJSP.parquet'
    WHERE partition_date BETWEEN '2025-01-01' AND '2025-03-31'
    GROUP BY winner_lawyer_oab, winner_lawyer_state
    ORDER BY wins DESC
    LIMIT 100
""").df()

# Downloaded: ONLY 2.25 GB (not 12 GB for all tribunals!)
# Query is fast due to selective file filtering
```

---

## 📤 Upload Strategy

### Initial Upload (Backfill)
For each date and tribunal in history:
1. Query DuckDB for all intimations on that date for that tribunal
2. Export to Parquet file named `causaganha-{YYYY}-{MM}-{DD}-{TRIBUNAL}.parquet`
3. Upload to IA with metadata
4. Record IA URL in local database

### Incremental Updates (Daily Export Pipeline)
1. **Collection**: Throughout the day, collect intimations from all 90 tribunals
2. **Analysis**: Analyze with LLM/RAG as they arrive
3. **Storage**: Store in DuckDB (working database)
4. **Daily Export** (runs at 02:00 UTC each day):
   - Export previous day's complete data to Parquet (per tribunal)
   - Example: On Jan 16 at 02:00, export all Jan 15 data
   - Creates ~90 files: causaganha-2025-01-15-{TRIBUNAL}.parquet
   - Upload all files to IA with metadata
   - Record exports in database
   - Purge old data from DuckDB (> 6 months)

**Frequency**: ~90 Parquet files per day (32,850 files/year)

**Note**: Parquet files are **immutable**. Don't update existing files; create new versions if corrections are needed.

---

## 🔄 Update Strategy for Corrections

### Problem
What if an analysis is wrong and corrected later?

### Solution Options

**Option A: Versioned Files**
```
causaganha-2025-01-15-TJRO-v1.parquet  # Original
causaganha-2025-01-15-TJRO-v2.parquet  # Corrected
```

**Option B: Separate Corrections Table**
```
causaganha-2025-01-15-TJRO.parquet              # Original data
causaganha-2025-01-15-TJRO-corrections.parquet  # Corrections
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

### Per Day (270,000 decisions across 90 tribunals)
- Raw JSON: ~1.35 GB total
- Parquet (compressed): **~135 MB total** (varies by tribunal)
- Files created: **~90 files per day** (one per tribunal)
- File sizes:
  - Small tribunals (TJRO): ~1.5 MB (3K decisions)
  - Medium tribunals (TJMG): ~12 MB (25K decisions)
  - Large tribunals (TJSP): ~25 MB (50K decisions)

### Per Month
- Files: ~2,700 files (90 tribunals × 30 days)
- Total storage: ~4 GB/month (135 MB/day × 30 days)
- Cost on IA: **$0**

### Year 1 (Production Scale)
- Total files: **32,850 files** (90 tribunals × 365 days)
- Total storage: ~49 GB (135 MB/day × 365 days)
- Decisions: ~100 million
- Cost on IA: **$0**
- Cost on AWS S3: **~$650/year (storage + bandwidth)**

### Year 5 (At Scale)
- Total files: **164,250 files** (32,850 × 5 years)
- Total storage: ~245 GB
- Decisions: ~500 million
- Cost on IA: **$0**
- Cost on AWS S3: **~$3,000/year + bandwidth**

---

## 🎯 Implementation Checklist

### Phase 1: MVP (Current)
- [ ] Define Parquet schema with daily+tribunal partitioning
- [ ] Implement export from DuckDB to Parquet (per tribunal)
- [ ] Implement IA upload with metadata
- [ ] Test with single day export for one tribunal (2025-01-15-TJRO)
- [ ] Verify query performance with ~3K rows per file
- [ ] Test wildcard queries across multiple tribunals

### Phase 2: Automation
- [ ] Daily pipeline exports previous day at 02:00 UTC (~90 files)
- [ ] Automated upload to Internet Archive (parallel uploads)
- [ ] Backfill historical data (daily+tribunal files)
- [ ] Document query patterns for selective downloads

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
