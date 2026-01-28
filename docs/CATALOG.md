# CausaGanha Catalog System

The catalog system provides a master index of all DJEN data stored on Internet Archive, enabling easy discovery, querying, and backfill tracking.

## Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          CATALOG SYSTEM                                       │
└──────────────────────────────────────────────────────────────────────────────┘

Internet Archive                          Local Machine
┌────────────────────┐                   ┌────────────────────────────────────┐
│ causaganha-catalog │   ──download──▶   │ ./causaganha-catalog/              │
│ ├── manifest.parquet                   │ ├── manifest.parquet    (file index)│
│ ├── backfill-needed.parquet            │ ├── backfill-needed.parquet        │
│ ├── catalog.sql                        │ ├── catalog.sql                     │
│ └── catalog.duckdb                     │ └── catalog.duckdb      (queryable) │
└────────────────────┘                   └────────────────────────────────────┘
        ▲                                              │
        │                                              ▼
        │                                ┌────────────────────────────────────┐
        │                                │     Query Remote Data Directly     │
        │                                │                                     │
   upload (daily)                        │  SELECT * FROM comunicacoes        │
        │                                │  WHERE tribunal = 'TJSP'           │
        │                                │  AND date >= '2026-01-01'          │
        │                                │                                     │
┌───────┴───────────┐                    │  → Fetches from IA automatically   │
│ GitHub Actions    │                    └────────────────────────────────────┘
│ update-catalog.yml│
└───────────────────┘
```

## Files

| File | Description |
|------|-------------|
| `manifest.parquet` | Index of all files on Internet Archive (filename, date, tribunal, size, type) |
| `backfill-needed.parquet` | List of missing data (date, tribunal, reason) |
| `catalog.sql` | SQL view definitions (portable, human-readable) |
| `catalog.duckdb` | Ready-to-use DuckDB database with remote views |

## Quick Start

### 1. Download Catalog

```bash
# Download catalog from Internet Archive
causaganha catalog download

# Force re-download
causaganha catalog download --force

# Custom output directory
causaganha catalog download --output ./my-catalog
```

### 2. Check Backfill Status

```bash
# Show what data is missing
causaganha catalog backfill-status

# Filter by tribunal
causaganha catalog backfill-status --tribunal TJSP

# Show more results
causaganha catalog backfill-status --limit 50
```

Example output:

```
📊 Backfill Status:

  Total missing: 5,000 items
  Tribunals: 91
  Days: 150
  Date range: 2024-01-01 to 2026-01-28

📋 Missing by Tribunal:
  TJSP  :  200 items (2024-01-01 to 2026-01-28)
  TJRJ  :  180 items (2024-01-01 to 2026-01-28)
  TJMG  :  175 items (2024-01-01 to 2026-01-28)
  ...
```

### 3. Query the Catalog

```bash
# Query manifest
causaganha catalog query "SELECT * FROM manifest WHERE tribunal = 'TJSP' LIMIT 10"

# Export as CSV
causaganha catalog query "SELECT * FROM manifest" --format csv

# Export as JSON
causaganha catalog query "SELECT * FROM backfill_needed" --format json
```

## Remote Data Access

The catalog includes views that query remote Parquet files directly from Internet Archive:

```sql
-- Connect to catalog
duckdb causaganha-catalog/catalog.duckdb

-- Query remote data (no download needed!)
SELECT COUNT(*) FROM comunicacoes WHERE tribunal = 'TJSP';

-- Get lawyer statistics
SELECT tribunal, COUNT(DISTINCT oab) as lawyers
FROM advogados
GROUP BY tribunal
ORDER BY lawyers DESC;
```

DuckDB automatically handles:
- HTTP range requests (fetches only needed data)
- Predicate pushdown (filters at source)
- Caching (repeated queries are faster)

## Manifest Schema

```sql
CREATE TABLE manifest (
    filename VARCHAR,     -- Full filename on IA
    item_id VARCHAR,      -- IA item identifier (e.g., djen-2026-01-15)
    date DATE,            -- Date of the data
    tribunal VARCHAR,     -- Tribunal code (e.g., TJSP)
    file_type VARCHAR,    -- zip, parquet, etc.
    size_bytes BIGINT     -- File size in bytes
);
```

## Backfill Schema

```sql
CREATE TABLE backfill_needed (
    date DATE,            -- Missing date
    tribunal VARCHAR,     -- Missing tribunal
    reason VARCHAR        -- Why it's missing (not_collected, conversion_failed, etc.)
);
```

## Catalog Generation

The catalog is generated daily by GitHub Actions:

```yaml
# .github/workflows/update-catalog.yml
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
```

To manually generate:

```bash
# Run the generation script
python scripts/generate_catalog.py --output-dir ./output

# This creates:
# - manifest.parquet
# - backfill-needed.parquet
# - catalog.sql
# - catalog.duckdb
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `causaganha catalog download` | Download catalog from Internet Archive |
| `causaganha catalog backfill-status` | Show what data needs to be collected |
| `causaganha catalog query <SQL>` | Query the catalog using SQL |
| `causaganha catalog create` | Create a local metadata catalog |
| `causaganha catalog list <path>` | List views in a catalog |
| `causaganha catalog info <path>` | Show catalog information |
| `causaganha catalog validate <path>` | Validate a catalog database |

## Use Cases

### 1. Discover Available Data

```sql
-- What dates have data?
SELECT DISTINCT date FROM manifest ORDER BY date DESC LIMIT 30;

-- What tribunals are covered?
SELECT tribunal, COUNT(*) as files
FROM manifest
GROUP BY tribunal
ORDER BY files DESC;

-- Data size by month
SELECT strftime(date, '%Y-%m') as month, SUM(size_bytes) / 1e9 as gb
FROM manifest
GROUP BY month
ORDER BY month;
```

### 2. Plan Backfill

```sql
-- Which tribunals need most backfill?
SELECT tribunal, COUNT(*) as missing_days
FROM backfill_needed
GROUP BY tribunal
ORDER BY missing_days DESC
LIMIT 10;

-- Missing dates for specific tribunal
SELECT date FROM backfill_needed
WHERE tribunal = 'TJSP'
ORDER BY date;
```

### 3. Query Remote Data

```sql
-- Count communications by tribunal (queries IA directly)
SELECT tribunal, COUNT(*) as total
FROM comunicacoes
GROUP BY tribunal
ORDER BY total DESC;

-- Export subset to local file
COPY (
    SELECT * FROM comunicacoes
    WHERE tribunal = 'TJSP' AND date >= '2026-01-01'
) TO 'tjsp_2026.parquet';
```

## Internet Archive Item

The catalog is stored at: https://archive.org/details/causaganha-catalog

Files:
- `manifest.parquet` - Updated daily
- `backfill-needed.parquet` - Updated daily
- `catalog.sql` - View definitions
- `catalog.duckdb` - Ready-to-use database

## Troubleshooting

### Catalog not found

```
❌ Backfill file not found: ./causaganha-catalog/backfill-needed.parquet
Run 'causaganha catalog download' first.
```

**Solution**: Download the catalog first:
```bash
causaganha catalog download
```

### Network errors

If Internet Archive is slow or unavailable:
1. Check https://archive.org/details/causaganha-catalog in browser
2. Try again later
3. Use `--force` to retry failed downloads

### Query errors

```
Error: Table 'comunicacoes' does not exist
```

**Solution**: Ensure you're using the correct catalog file:
```bash
duckdb causaganha-catalog/catalog.duckdb
```
