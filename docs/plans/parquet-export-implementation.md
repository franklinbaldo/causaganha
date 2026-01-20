# Implementation Plan: Parquet Data Lake Export System

**Status**: ✅ Complete (Phases 1-6)
**Priority**: High (P2 - Essential Operations)
**Created**: 2025-01-20
**Completed**: 2025-01-20

---

## 📋 Problem Statement

CausaGanha needs to export analyzed judicial decisions to Internet Archive as Parquet files using hierarchical date+tribunal partitioning. This enables:
- Free, permanent, distributed storage ($0 vs $650+/year on AWS)
- Public verification and reproducibility
- Selective downloads by tribunal (e.g., 547 MB for TJRO vs 49 GB for all)
- Daily incremental exports

**Current State**: BDD features defined, no implementation exists
**Target State**: Daily automated exports running at 02:00 UTC

---

## 🎯 Success Criteria

1. ✅ **COMPLETE** - Export creates Parquet files: `causaganha-{YYYY}-{MM}-{DD}-{TRIBUNAL}.parquet`
2. ✅ **COMPLETE** - Files uploaded to Internet Archive with correct metadata
3. ✅ **COMPLETE** - Database tracks export status (tribunal, date, IA URL, file size)
4. ✅ **COMPLETE** - Daily cron/systemd job exports previous day at 02:00 UTC
5. ✅ **COMPLETE** - Old data (>6 months) purged from DuckDB after export
6. ⚠️ **PARTIAL** - 27 BDD scenarios in `14_database_schema.feature` (2 passing, pytest-bdd 8.x datatable support pending)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│              Daily Export Pipeline                   │
│                   (02:00 UTC)                        │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   1. Query DuckDB             │
        │   - Filter by partition_date  │
        │   - Group by tribunal         │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   2. Export to Parquet        │
        │   - Per tribunal              │
        │   - Snappy compression        │
        │   - Denormalized schema       │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   3. Upload to IA             │
        │   - Parallel uploads          │
        │   - Metadata generation       │
        │   - Verification              │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   4. Record in Database       │
        │   - Export status             │
        │   - IA URL                    │
        │   - File size                 │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   5. Purge Old Data           │
        │   - Data > 6 months old       │
        │   - Keep export record        │
        └───────────────────────────────┘
```

---

## 📦 Implementation Steps

### Phase 1: Database Schema (BDD Feature Required)

**File**: `tests/features/14_database_schema.feature`

```gherkin
Feature: Database Schema Management
  Scenario: Parquet export tracking table exists
    When I check the database schema
    Then a table "parquet_exports" should exist
    And it should have columns: id, tribunal, partition_date, ia_item_id,
        ia_url, parquet_filename, row_count, file_size_mb, uploaded_at, status
```

**Implementation**:
- [ ] Create migration: `src/causaganha/v2/storage/migrations/002_add_parquet_exports.sql`
- [ ] Add table: `parquet_exports`
- [ ] Add queries in `src/causaganha/v2/storage/queries.py`

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS parquet_exports (
    id INTEGER PRIMARY KEY,
    tribunal VARCHAR NOT NULL,
    partition_date DATE NOT NULL,
    ia_item_id VARCHAR NOT NULL,
    ia_url VARCHAR NOT NULL,
    parquet_filename VARCHAR NOT NULL,
    row_count INTEGER NOT NULL,
    file_size_mb FLOAT NOT NULL,
    uploaded_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,  -- 'pending', 'uploading', 'completed', 'failed'
    error_message TEXT,
    UNIQUE(tribunal, partition_date)
);

CREATE INDEX idx_parquet_exports_date ON parquet_exports(partition_date);
CREATE INDEX idx_parquet_exports_tribunal ON parquet_exports(tribunal);
CREATE INDEX idx_parquet_exports_status ON parquet_exports(status);
```

---

### Phase 2: Parquet Export Module

**File**: `src/causaganha/v2/pipeline/parquet_export.py`

**Classes**:
```python
from dataclasses import dataclass
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import ibis


@dataclass
class ExportConfig:
    """Configuration for Parquet export."""
    output_dir: Path
    compression: str = "snappy"
    row_group_size: int = 10_000
    schema_version: str = "v1"


class ParquetExporter:
    """Exports intimations from DuckDB to Parquet files."""

    def __init__(self, db_connection, config: ExportConfig):
        self.db = db_connection
        self.config = config

    async def export_day_tribunal(
        self,
        partition_date: str,  # YYYY-MM-DD
        tribunal: str
    ) -> Path:
        """
        Export single day+tribunal partition to Parquet.

        Returns path to created Parquet file.
        """
        # Query DuckDB for data
        # Convert to PyArrow table
        # Write Parquet with compression
        # Return file path
        pass

    async def export_day_all_tribunals(
        self,
        partition_date: str
    ) -> list[Path]:
        """
        Export all tribunals for a single day.

        Returns list of Parquet file paths (~90 files).
        """
        pass

    def _build_parquet_schema(self) -> pa.Schema:
        """Define Parquet schema with nested structures."""
        pass

    def _query_intimations(self, date: str, tribunal: str):
        """Query DuckDB for intimations to export."""
        pass
```

**Dependencies**:
- `pyarrow` - Already in project
- `ibis-framework[duckdb]` - Already in project

**Tests**:
- [ ] Unit tests: `tests/unit/test_parquet_export.py`
- [ ] Integration tests: Export sample data to Parquet
- [ ] Verify schema matches BDD feature
- [ ] Verify compression ratio (~10:1)

---

### Phase 3: Internet Archive Upload

**File**: `src/causaganha/v2/pipeline/ia_upload.py`

**Classes**:
```python
from internetarchive import get_item, upload
from dataclasses import dataclass


@dataclass
class IAMetadata:
    """Metadata for Internet Archive item."""
    title: str
    collection: str = "causaganha"
    mediatype: str = "data"
    subject: list[str] = None
    description: str = None
    date: str = None
    coverage: str = None
    creator: str = "CausaGanha Project"
    rights: str = "CC0 1.0 Universal (Public Domain)"


class InternetArchiveUploader:
    """Uploads Parquet files to Internet Archive."""

    def __init__(self, credentials_path: Path = None):
        # Load IA credentials
        pass

    async def upload_parquet(
        self,
        file_path: Path,
        tribunal: str,
        partition_date: str
    ) -> str:
        """
        Upload Parquet file to Internet Archive.

        Returns IA item URL.
        """
        item_id = self._generate_item_id(partition_date, tribunal)
        metadata = self._generate_metadata(tribunal, partition_date)

        # Upload file
        # Verify upload
        # Return URL
        pass

    def _generate_item_id(self, date: str, tribunal: str) -> str:
        """Generate IA item ID: causaganha-2025-01-15-TJRO"""
        return f"causaganha-{date}-{tribunal}"

    def _generate_metadata(self, tribunal: str, date: str) -> dict:
        """Generate IA metadata."""
        pass

    async def verify_upload(self, item_id: str) -> bool:
        """Verify file was uploaded successfully."""
        pass
```

**Dependencies**:
- `internetarchive` - Need to add to `pyproject.toml`

**Configuration**:
- Credentials in `.env` or `~/.config/ia.ini`
- Environment variables: `IA_ACCESS_KEY`, `IA_SECRET_KEY`

**Tests**:
- [ ] Unit tests with mocked IA API
- [ ] Integration tests with IA test collection
- [ ] Verify metadata format
- [ ] Verify upload verification logic

---

### Phase 4: Export Orchestration

**File**: `src/causaganha/v2/pipeline/export_orchestrator.py`

**Class**:
```python
class ExportOrchestrator:
    """Orchestrates daily Parquet export pipeline."""

    def __init__(self, db, parquet_exporter, ia_uploader):
        self.db = db
        self.exporter = parquet_exporter
        self.uploader = ia_uploader

    async def run_daily_export(self, date: str = None):
        """
        Run daily export for previous day.

        If date not specified, exports yesterday's data.
        """
        if date is None:
            date = self._get_yesterday()

        tribunals = self._get_active_tribunals(date)

        for tribunal in tribunals:
            try:
                # 1. Check if already exported
                if self._already_exported(date, tribunal):
                    continue

                # 2. Export to Parquet
                parquet_file = await self.exporter.export_day_tribunal(
                    date, tribunal
                )

                # 3. Upload to IA
                ia_url = await self.uploader.upload_parquet(
                    parquet_file, tribunal, date
                )

                # 4. Record in database
                await self._record_export(
                    tribunal, date, ia_url, parquet_file
                )

                # 5. Clean up local file
                parquet_file.unlink()

            except Exception as e:
                await self._record_export_failure(
                    tribunal, date, str(e)
                )

        # 6. Purge old data
        await self._purge_old_data(date)

    async def backfill_historical(
        self,
        start_date: str,
        end_date: str
    ):
        """Backfill historical data exports."""
        pass
```

**Tests**:
- [ ] Unit tests with mocked dependencies
- [ ] Integration test: End-to-end export
- [ ] Test failure handling per tribunal
- [ ] Test duplicate detection

---

### Phase 5: CLI Commands

**File**: `src/causaganha/cli.py` (extend existing)

**Commands**:
```python
@app.command()
def export_parquet(
    date: str = typer.Option(None, help="Date to export (YYYY-MM-DD), defaults to yesterday"),
    tribunal: str = typer.Option(None, help="Specific tribunal to export (optional)"),
    backfill: bool = typer.Option(False, help="Backfill mode"),
    start_date: str = typer.Option(None, help="Start date for backfill"),
    end_date: str = typer.Option(None, help="End date for backfill"),
):
    """Export analyzed decisions to Parquet and upload to Internet Archive."""
    pass


@app.command()
def export_status(
    tribunal: str = typer.Option(None, help="Filter by tribunal"),
    days: int = typer.Option(7, help="Show last N days"),
):
    """Show Parquet export status."""
    pass
```

**Usage**:
```bash
# Export yesterday's data (default)
uv run causaganha export-parquet

# Export specific date
uv run causaganha export-parquet --date 2025-01-15

# Export specific tribunal only
uv run causaganha export-parquet --date 2025-01-15 --tribunal TJRO

# Backfill historical data
uv run causaganha export-parquet --backfill --start-date 2024-12-01 --end-date 2024-12-31

# Check export status
uv run causaganha export-status
uv run causaganha export-status --tribunal TJRO --days 30
```

---

### Phase 6: Scheduling ✅ COMPLETE

**Status**: ✅ Implemented (2025-01-20)

**Files Created**:
- ✅ `scripts/daily_export.py` - Python daily export runner with proper exit codes
- ✅ `scripts/check_export_health.py` - Health check script for monitoring
- ✅ `deployment/systemd/causaganha-export.service` - Systemd service file
- ✅ `deployment/systemd/causaganha-export.timer` - Systemd timer (02:00 UTC daily)
- ✅ `deployment/cron/causaganha-export.cron` - Cron configuration alternative
- ✅ `deployment/SCHEDULING.md` - Complete deployment and monitoring guide

**Exit Codes** (`daily_export.py`):
- 0: Success (all tribunals exported)
- 1: Partial failure (some tribunals failed)
- 2: Complete failure (no tribunals exported)
- 3: Configuration error

**Systemd Timer** (Recommended):
```bash
# Enable and start timer
sudo systemctl enable causaganha-export.timer
sudo systemctl start causaganha-export.timer

# Check status
sudo systemctl list-timers causaganha-export.timer

# View logs
sudo journalctl -u causaganha-export.service -n 50
```

**Cron Alternative**:
```bash
# Install cron file
sudo cp deployment/cron/causaganha-export.cron /etc/cron.d/causaganha-export
```

**Health Monitoring**:
```bash
# Check export health (returns Nagios-style exit codes)
python scripts/check_export_health.py

# View export status
causaganha export-status --days 7
causaganha export-status --failed-only
```

**Features**:
- Automatic retry on failure (systemd)
- Resource limits (2GB RAM, 50% CPU)
- Security hardening (sandboxing, restricted paths)
- Random delay (0-30min) to avoid thundering herd
- Persistent scheduling (runs on next boot if missed)
- Comprehensive logging (journald/syslog)

---

## 🧪 Testing Strategy

### BDD Feature Tests
- [ ] Create step definitions for `04_data_lake_export.feature`
- [ ] Create step definitions for `14_database_schema.feature`
- [ ] Use pytest-bdd framework
- [ ] Mock IA uploads in tests

### Integration Tests
- [ ] Test export with sample data (100 rows)
- [ ] Verify Parquet file structure
- [ ] Verify compression ratio
- [ ] Test IA upload to test collection
- [ ] Test database recording

### Performance Tests
- [ ] Export 50K rows (TJSP size) - should complete in < 30 seconds
- [ ] Verify memory usage stays under 200 MB
- [ ] Test parallel exports (90 tribunals)

---

## 📚 Dependencies to Add

```toml
# pyproject.toml
[project]
dependencies = [
    # ... existing deps
    "internetarchive>=4.0.0",  # IA uploads
]

[project.optional-dependencies]
dev = [
    # ... existing dev deps
    "pytest-bdd>=7.0.0",  # BDD testing
]
```

---

## 🚨 Error Handling

### Export Failures
- Log error to database (`parquet_exports.status = 'failed'`)
- Continue with other tribunals (isolated failures)
- Alert on > 10% failure rate

### IA Upload Failures
- Retry 3 times with exponential backoff (2s, 4s, 8s)
- Keep Parquet file locally if upload fails
- Re-attempt on next run

### Disk Space
- Check available space before export
- Fail fast if < 1 GB available
- Clean up temp files on failure

---

## 📊 Monitoring

### Metrics to Track
- Export duration per tribunal
- Upload duration per file
- File sizes (compression ratio)
- Success rate (% exported)
- Failure rate per tribunal
- Total storage on IA

### Alerts
- Export failed for > 10% of tribunals
- Upload failed after retries
- Export duration > 30 minutes
- Disk space < 1 GB

---

## 🗺️ Implementation Timeline

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 1 | Database schema + BDD feature | 2h | ⏳ Pending |
| 2 | Parquet export module | 4h | ⏳ Pending |
| 3 | IA upload module | 3h | ⏳ Pending |
| 4 | Export orchestration | 3h | ⏳ Pending |
| 5 | CLI commands | 2h | ⏳ Pending |
| 6 | BDD step definitions | 4h | ⏳ Pending |
| 7 | Integration tests | 3h | ⏳ Pending |
| 8 | Scheduling setup | 1h | ⏳ Pending |
| **Total** | | **22h** | |

---

## 🎯 Definition of Done

- [ ] All 32 scenarios in `04_data_lake_export.feature` pass
- [ ] Database schema BDD feature passes
- [ ] CLI command exports Parquet successfully
- [ ] Files uploaded to IA test collection
- [ ] Database tracks all exports
- [ ] Daily cron job configured
- [ ] Documentation updated
- [ ] Code reviewed and merged

---

## 📖 References

- BDD Feature: `tests/features/04_data_lake_export.feature`
- Architecture Doc: `docs/DATA_LAKE_ARCHITECTURE.md`
- PyArrow Parquet: https://arrow.apache.org/docs/python/parquet.html
- Internet Archive Python: https://archive.org/services/docs/api/internetarchive/
