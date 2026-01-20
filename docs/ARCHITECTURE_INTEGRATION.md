# Architecture Integration: Parquet Export System

This document explains how the new Parquet export system integrates with the existing CausaGanha V2 architecture.

## 📊 Complete Data Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    CausaGanha V2 Pipeline                      │
└────────────────────────────────────────────────────────────────┘

┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  1. COLLECT │ ───► │  2. ANALYZE │ ───► │  3. EXPORT  │ ◄── NEW!
└─────────────┘      └─────────────┘      └─────────────┘
      │                     │                     │
      ▼                     ▼                     ▼
   PJe API            Pydantic AI          Internet Archive
  (Intimations)        (Winners)          (Parquet Files)
      │                     │                     │
      ▼                     ▼                     ▼
┌──────────────────────────────────────────────────────────┐
│                       DuckDB Storage                      │
│  ┌────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │intimations │  │decision_analysis│  │parquet_exports│ │  ◄── NEW!
│  │            │  │                 │  │              │ │
│  │ • id       │  │ • intimation_id │  │ • tribunal   │ │
│  │ • tribunal │  │ • winner_oab    │  │ • date       │ │
│  │ • date     │  │ • loser_oab     │  │ • ia_url     │ │
│  │ • process  │  │ • confidence    │  │ • status     │ │
│  │ • text     │  │ • model_used    │  │              │ │
│  └────────────┘  └─────────────────┘  └──────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 🏗️ Module Integration

### Existing V2 Modules

```
src/causaganha/v2/
├── api/
│   └── client.py              # PJe API client (existing)
│
├── pipeline/
│   ├── collect.py             # Step 1: Collect intimations (existing)
│   ├── analyze.py             # Step 2: Analyze with Gemini (existing)
│   ├── score.py               # Compute lawyer ratings (existing)
│   ├── archive.py             # Archive PDFs to IA (existing)
│   │
│   ├── parquet_export.py      # NEW: Export to Parquet
│   ├── ia_upload.py           # NEW: Upload Parquet to IA
│   └── export_orchestrator.py # NEW: Coordinate export pipeline
│
├── storage/
│   ├── connection.py          # DuckDB connection (existing, reused)
│   ├── schema.sql             # Table definitions (existing, reused)
│   ├── queries.py             # Query functions (existing, reused)
│   └── migrations/
│       ├── 001_*.sql          # Existing migration
│       └── 002_*.sql          # NEW: parquet_exports table
│
└── analysis/
    ├── hybrid_analyzer.py     # Analysis logic (existing)
    └── rag_analyzer.py        # RAG analysis (existing)
```

### Integration Points

#### 1. **Database Connection** (Reused)
```python
# NEW modules use existing connection
from causaganha.v2.storage.connection import get_connection

con = get_connection()  # Same DuckDB instance used by collect/analyze
```

#### 2. **Storage Schema** (Extended)
```sql
-- EXISTING tables (used by collect.py, analyze.py)
intimations           -- Source data from PJe API
decision_analysis     -- Analysis results from Gemini

-- NEW table (used by export_orchestrator.py)
parquet_exports       -- Export tracking and metadata
```

#### 3. **CLI Commands** (Extended)
```python
# src/causaganha/cli.py

# EXISTING commands
causaganha collect      # Calls pipeline.collect
causaganha analyze      # Calls pipeline.analyze
causaganha db init      # Creates schema
causaganha db migrate   # Runs migrations (updated to run ALL)

# NEW commands
causaganha export-parquet   # Calls export_orchestrator
causaganha export-status    # Queries parquet_exports table
```

---

## 🔄 Complete Pipeline Flow

### Phase 1: Collection (Existing)
```python
# src/causaganha/v2/pipeline/collect.py

from causaganha.v2.api.client import PJeAPIClient
from causaganha.v2.storage.connection import get_connection

# 1. Fetch intimations from PJe API
client = PJeAPIClient()
intimations = await client.get_intimations_by_court("TJRO", date="2025-01-15")

# 2. Store in DuckDB
con = get_connection()
con.insert("intimations", intimations)

# Result: intimations table populated
```

### Phase 2: Analysis (Existing)
```python
# src/causaganha/v2/pipeline/analyze.py

from causaganha.v2.analysis.hybrid_analyzer import HybridAnalyzer
from causaganha.v2.storage.queries import get_unanalyzed_intimations

# 1. Get unanalyzed intimations
intimations = get_unanalyzed_intimations()

# 2. Analyze with Gemini
analyzer = HybridAnalyzer()
for intimation in intimations:
    result = await analyzer.analyze(intimation)
    store_analysis(result)

# Result: decision_analysis table populated
```

### Phase 3: Export (NEW)
```python
# src/causaganha/v2/pipeline/export_orchestrator.py

from causaganha.v2.pipeline.parquet_export import ParquetExporter
from causaganha.v2.pipeline.ia_upload import InternetArchiveUploader

# 1. Query joined data (intimations + decision_analysis)
exporter = ParquetExporter(con)
file_path, row_count = await exporter.export_day_tribunal(
    partition_date="2025-01-15",
    tribunal="TJRO"
)

# 2. Upload to Internet Archive
uploader = InternetArchiveUploader()
ia_url = await uploader.upload_parquet(file_path, "TJRO", "2025-01-15")

# 3. Record in database
con.insert("parquet_exports", {
    "tribunal": "TJRO",
    "partition_date": "2025-01-15",
    "ia_url": ia_url,
    "row_count": row_count,
    "status": "completed"
})

# 4. Purge old data (>6 months)
con.delete("intimations", "data_disponibilizacao < '2024-07-15'")

# Result: Parquet file on IA, local data cleaned up
```

---

## 📦 Data Schema Integration

### Denormalized Parquet Schema

The Parquet export **joins** existing tables to create a denormalized structure:

```python
# src/causaganha/v2/pipeline/parquet_export.py

def _query_intimations(self, date: str, tribunal: str):
    """Query DuckDB for intimations to export."""

    # Join intimations + decision_analysis
    intimations = self.db.table("intimations")
    analysis = self.db.table("decision_analysis")

    query = (
        intimations
        .left_join(analysis, intimations.id == analysis.intimation_id)
        .filter(
            (intimations.data_disponibilizacao == date)
            & (intimations.sigla_tribunal == tribunal)
        )
        .select(
            # From intimations table
            intimation_id=intimations.id,
            numero_processo=intimations.numero_processo,
            data_disponibilizacao=intimations.data_disponibilizacao,
            sigla_tribunal=intimations.sigla_tribunal,
            texto=intimations.texto,
            tipo_documento=intimations.tipo_documento,

            # From decision_analysis table
            winner_lawyer_oab=analysis.winner_lawyer_oab,
            winner_lawyer_state=analysis.winner_lawyer_state,
            loser_lawyer_oab=analysis.loser_lawyer_oab,
            loser_lawyer_state=analysis.loser_lawyer_state,
            confidence_score=analysis.confidence_score,
            decision_type=analysis.decision_type,
            model_used=analysis.model_used,
        )
    )

    return query.to_pyarrow()
```

**Result**: Single Parquet file contains all data needed for analysis (no joins required).

---

## 🔗 CLI Integration

### Existing CLI Flow
```bash
# Daily operation (existing)
causaganha collect --courts TJRO      # Populate intimations
causaganha analyze                    # Populate decision_analysis
causaganha score                      # Update lawyer ratings
```

### New Integrated Flow
```bash
# Daily operation (with new export)
causaganha collect --courts TJRO      # 1. Collect
causaganha analyze                    # 2. Analyze
causaganha export-parquet             # 3. Export ◄── NEW!

# Result:
# - DuckDB has recent data (last 6 months)
# - Internet Archive has all historical data (forever)
# - parquet_exports table tracks what's been exported
```

---

## 📅 Automated Schedule Integration

### Daily Automation (NEW)

```bash
# Systemd timer runs at 02:00 UTC
/etc/systemd/system/causaganha-export.timer

[Timer]
OnCalendar=*-*-* 02:00:00 UTC
```

**Timeline**:
```
00:00 - 01:00 UTC: Collection & Analysis (existing cron jobs)
                   ├── causaganha collect
                   └── causaganha analyze

02:00 - 03:00 UTC: Export to IA (NEW systemd timer)
                   └── python scripts/daily_export.py
                       └── causaganha export-parquet
                           ├── Query yesterday's data
                           ├── Export to Parquet
                           ├── Upload to Internet Archive
                           └── Purge data >6 months old
```

---

## 🗄️ Storage Lifecycle

### Data Retention Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    Data Lifecycle                        │
└─────────────────────────────────────────────────────────┘

Day 0: Collection
├── PJe API → intimations table (raw data)
└── Status: "pending analysis"

Day 1: Analysis
├── Gemini AI → decision_analysis table (results)
└── Status: "analyzed"

Day 1 (02:00 UTC): Export
├── DuckDB → Parquet file (denormalized)
├── Parquet → Internet Archive (permanent)
├── Metadata → parquet_exports table (tracking)
└── Status: "exported"

Day 180 (6 months): Cleanup
├── Delete from intimations table
├── Delete from decision_analysis table
├── Keep in parquet_exports table (metadata only)
└── Keep on Internet Archive (actual data)

Result:
- DuckDB: Working set (last 6 months, ~50 GB)
- Internet Archive: Full history (all time, ~500 GB, $0)
```

---

## 🔍 Query Integration

### Queries Across Storage Layers

**Recent Data** (last 6 months):
```python
# Query DuckDB directly (fast)
from causaganha.v2.storage.connection import get_connection

con = get_connection()
recent = con.sql("""
    SELECT * FROM intimations
    WHERE data_disponibilizacao >= current_date - INTERVAL 6 MONTHS
""").to_pyarrow()
```

**Historical Data** (older than 6 months):
```python
# Query Parquet files from Internet Archive
import pyarrow.parquet as pq

# Download specific partition
ia_url = "https://archive.org/download/causaganha-2024-01-15-TJRO/causaganha-2024-01-15-TJRO.parquet"
table = pq.read_table(ia_url)

# Or query locally downloaded files
table = pq.read_table("exports/causaganha-2024-01-15-TJRO.parquet")
df = table.to_pandas()
```

**Combined Queries** (recent + historical):
```python
# Query recent from DuckDB
recent_df = con.sql("SELECT * FROM intimations WHERE ...").to_pandas()

# Query historical from Parquet
historical_df = pq.read_table("exports/*.parquet").to_pandas()

# Combine
combined_df = pd.concat([recent_df, historical_df])
```

---

## 🔄 Migration Path

### Database Schema Evolution

```sql
-- Migration 001: Base schema (existing)
CREATE TABLE intimations (...);
CREATE TABLE decision_analysis (...);
CREATE TABLE intimation_lawyers (...);

-- Migration 002: Export tracking (NEW)
CREATE SEQUENCE parquet_exports_id_seq;
CREATE TABLE parquet_exports (
    id INTEGER PRIMARY KEY DEFAULT nextval('parquet_exports_id_seq'),
    tribunal VARCHAR NOT NULL,
    partition_date DATE NOT NULL,
    ia_url VARCHAR NOT NULL,
    ...
);
CREATE VIEW export_statistics AS ...;
CREATE VIEW problematic_tribunals AS ...;
```

**Apply Migrations**:
```bash
causaganha db migrate  # Applies ALL migrations in order
```

---

## 📊 Monitoring Integration

### Health Checks

**Database Health** (Existing):
```bash
causaganha db status
# Shows: tables, row counts, last updates
```

**Export Health** (NEW):
```bash
python scripts/check_export_health.py
# Returns: OK (0), WARNING (1), CRITICAL (2), UNKNOWN (3)

causaganha export-status --days 7
# Shows: success rates, failed tribunals, storage growth
```

**Combined Monitoring**:
```bash
# Check entire pipeline health
causaganha db status              # Collection/analysis status
python scripts/check_export_health.py  # Export status

# Query statistics
SELECT * FROM export_statistics ORDER BY partition_date DESC LIMIT 7;
SELECT * FROM problematic_tribunals WHERE failure_rate_pct > 10;
```

---

## 🎯 Key Integration Points Summary

| Component | Integration Point | How It Connects |
|-----------|-------------------|-----------------|
| **Database** | `get_connection()` | Reuses existing DuckDB connection |
| **Tables** | `intimations`, `decision_analysis` | Reads existing data for export |
| **Schema** | `schema.sql` + `002_*.sql` | Extends schema with export tracking |
| **CLI** | `cli.py` | Adds new commands alongside existing ones |
| **Pipeline** | `pipeline/` directory | New modules alongside collect/analyze |
| **Queries** | Ibis expressions | Uses same query layer as analysis |
| **Storage** | DuckDB → Parquet → IA | Extends storage with archival layer |
| **Scheduling** | Systemd/Cron | Runs after collection/analysis completes |

---

## 🚀 Benefits of Integration

### 1. **Seamless Data Flow**
- Collection → Analysis → Export happens automatically
- No data duplication or transformation required
- Single source of truth (DuckDB during processing)

### 2. **Cost Optimization**
- DuckDB: Fast queries on recent data
- Internet Archive: Free permanent storage
- Automatic cleanup prevents unbounded growth

### 3. **Backward Compatible**
- Existing pipelines unchanged
- Export system is additive (doesn't modify existing)
- Can be disabled without affecting core functionality

### 4. **Scalable Architecture**
- Partitioned by date + tribunal (selective downloads)
- Columnar format (10x compression)
- Distributed storage (Internet Archive's CDN)

### 5. **Maintainability**
- Follows V2 module structure
- Uses same patterns as existing code
- Clear separation of concerns

---

## 🔧 Configuration

### Environment Variables

```bash
# Existing (used by collect/analyze)
PJE_API_URL=https://comunicaapi.pje.jus.br/api/v1
GEMINI_API_KEY=your_key

# NEW (used by export)
IA_ACCESS_KEY=your_ia_access_key
IA_SECRET_KEY=your_ia_secret_key
```

### File Paths

```bash
# Existing
data/causaganha.duckdb          # DuckDB database (all modules use this)
data/lancedb/                   # Vector store (RAG analysis)

# NEW
data/exports/                   # Temporary Parquet files (auto-cleaned)
/var/log/causaganha/export.log  # Export logs
```

---

## 📝 Summary

The Parquet export system integrates seamlessly with CausaGanha V2 by:

1. **Reusing Existing Infrastructure**
   - Same DuckDB connection
   - Same table schemas
   - Same CLI framework

2. **Extending the Pipeline**
   - New step: Export (after collect/analyze)
   - New table: parquet_exports (tracking)
   - New commands: export-parquet, export-status

3. **Maintaining Separation**
   - Independent modules in `pipeline/`
   - Optional functionality (doesn't break existing)
   - Clear interfaces and contracts

4. **Providing Value**
   - Permanent archival storage ($0 cost)
   - Data lake for historical analysis
   - Automatic cleanup (6-month retention)
   - Public verification and reproducibility

The system is **production-ready** and can be deployed without modifying existing collection or analysis pipelines.
