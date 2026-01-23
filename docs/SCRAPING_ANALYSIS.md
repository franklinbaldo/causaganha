# 🔍 Scraping Architecture Analysis

## ❓ Question

> "The new scraping code is supposed to download data directly in **ZIP format** and upload directly to **Internet Archive**, then other workflow goes there download it and transform and normalize to **Parquet files** and upload again. Is this still in place? Does the `collect` command does anything like this? If not we don't need it."

---

## ✅ Answer: **NO, this is NOT implemented**

### Current Implementation (What EXISTS)

```
PJe API (JSON)
    ↓
collect.py (HTTP GET)
    ↓
DuckDB (local storage)
    ↓
[Later: analyze, score, etc.]
    ↓
export_orchestrator.py
    ↓
Parquet files → Internet Archive
```

**Flow**:
1. `causaganha collect` → Fetches **JSON** from PJe API → Stores in **DuckDB local**
2. `causaganha export-parquet` → Exports DuckDB → **Parquet** → Internet Archive

**NO ZIP DOWNLOAD/UPLOAD ANYWHERE!**

---

### Expected Implementation (What SHOULD exist)

```
PJe API (or scraper)
    ↓
Download RAW data as ZIP
    ↓
Upload ZIP directly to Internet Archive
    ↓
[Separate workflow]
    ↓
Download ZIP from Internet Archive
    ↓
Transform/Normalize → Parquet
    ↓
Upload Parquet to Internet Archive
```

**Flow**:
1. **Scraper** → Download raw data as **ZIP** → Upload to **Internet Archive**
2. **Transform workflow** → Download **ZIP** from IA → Normalize → **Parquet** → Upload to IA

---

## 📋 Current Code Audit

### 1. `collect.py` - What it ACTUALLY does

**File**: `src/causaganha/pipeline/collect.py`

**Current behavior**:
```python
async def collect_metadata_for_court(sigla_tribunal, days_back=7):
    """
    1. HTTP GET from PJe API (JSON format)
    2. Parse JSON response
    3. Store in DuckDB (local SQLite-like database)
    4. Extract lawyer associations
    5. Store lawyer associations in DuckDB

    Returns: Statistics dict
    """
    client = PJeAPIClient()
    intimations = await client.get_intimations_by_court(...)  # JSON

    # Store locally
    store_intimations(con, intimations)
    store_lawyer_associations(con, intimation.id, lawyers)
```

**What it does NOT do**:
- ❌ Download ZIP files
- ❌ Upload to Internet Archive
- ❌ Store raw data for later processing
- ❌ Preserve original format

**Verdict**: This is **OLD architecture**, NOT the new ZIP-based scraping.

---

### 2. Internet Archive Integration - What EXISTS

#### `ia_download.py` (450 lines)

**Purpose**: Download **PARQUET** files from Internet Archive.

```python
class IAParquetDownloader:
    """Downloads CausaGanha parquet files from Internet Archive."""

    async def download(self, tribunal: str, date: str) -> Path:
        """
        Download parquet file from IA.

        URL format:
        https://archive.org/download/causaganha-decisions-{date}-{tribunal}/
            causaganha-decisions-{date}-{tribunal}.parquet
        """
```

**What it does**:
- ✅ Download **Parquet** from IA
- ✅ Local caching
- ✅ Retry logic
- ❌ NO ZIP support

---

#### `ia_upload.py` (337 lines)

**Purpose**: Upload **PARQUET** files to Internet Archive.

```python
class InternetArchiveUploader:
    """Upload parquet files to Internet Archive."""

    async def upload(self, file_path: Path, metadata: dict) -> str:
        """Upload parquet file to IA."""
```

**What it does**:
- ✅ Upload **Parquet** to IA
- ✅ Metadata management
- ✅ Retry logic
- ❌ NO ZIP support

---

### 3. Export Pipeline - Current Flow

**File**: `src/causaganha/pipeline/export_orchestrator.py` (470 lines)

**Current flow**:
```python
# 1. Export from DuckDB to Parquet
parquet_exporter.export_decisions(tribunal, date)
parquet_exporter.export_embeddings(tribunal, date)
parquet_exporter.export_lawyers(date)

# 2. Upload Parquet to Internet Archive
ia_uploader.upload(parquet_file, metadata)
```

**Format**: Parquet (NOT ZIP)

---

## 🚨 Problems with Current Architecture

### 1. **No Raw Data Preservation**
- JSON from PJe API is **parsed immediately** and stored in DuckDB
- Original data is **lost**
- Cannot reprocess if parsing logic changes

### 2. **No ZIP Support**
- All code expects **Parquet** format
- No ZIP download/upload anywhere

### 3. **Local Storage Dependency**
- DuckDB is local (single machine)
- Cannot distribute processing

### 4. **Not Aligned with New Architecture**
- You described: **ZIP → IA → Transform → Parquet → IA**
- Current: **JSON → DuckDB → Parquet → IA**

---

## 🎯 Recommendation: Remove or Replace `collect` Command

### Option 1: **REMOVE** (If new scraper exists elsewhere)

If you have a **separate scraping system** that already:
- Downloads raw data as ZIP
- Uploads to Internet Archive

Then the current `collect` command is **redundant** and should be removed.

**Files to delete**:
```bash
src/causaganha/pipeline/collect.py
src/causaganha/api/client.py  # PJe API client (if only used by collect)
```

**Commands to remove from CLI**:
```python
# cli/__init__.py
@app.command()
def collect(...):  # ← DELETE THIS
    ...
```

---

### Option 2: **REPLACE** (If scraper needs to be implemented)

If the new scraping system **does NOT exist yet**, replace `collect` with new ZIP-based scraper.

**New architecture**:

```python
# src/causaganha/pipeline/scrape.py

async def scrape_tribunal_data(
    tribunal: str,
    date_range: tuple[date, date],
    format: str = "zip"  # ← NEW: Download as ZIP
) -> Path:
    """
    Download raw data from PJe API as ZIP.

    Returns:
        Path to downloaded ZIP file
    """
    # 1. Fetch data from PJe API (all endpoints)
    # 2. Bundle into ZIP file
    # 3. Return ZIP path (DO NOT store in DuckDB)


async def upload_raw_to_ia(
    zip_path: Path,
    tribunal: str,
    date: str
) -> str:
    """
    Upload raw ZIP to Internet Archive.

    Returns:
        IA URL
    """
    identifier = f"causaganha-raw-{date}-{tribunal}"

    item = ia.get_item(identifier)
    item.upload(
        zip_path,
        metadata={
            "collection": "causaganha-raw",
            "mediatype": "data",
            "format": "ZIP"
        }
    )

    return f"https://archive.org/download/{identifier}/{zip_path.name}"


# src/causaganha/pipeline/transform.py

async def transform_raw_to_parquet(
    tribunal: str,
    date: str
) -> list[Path]:
    """
    Download ZIP from IA, transform to Parquet, upload Parquet to IA.

    Flow:
    1. Download ZIP from IA (causaganha-raw-{date}-{tribunal}.zip)
    2. Extract and normalize data
    3. Export to Parquet (decisions, embeddings, lawyers)
    4. Upload Parquet to IA (causaganha-decisions-{date}-{tribunal}.parquet)
    5. Clean up temp files
    """
    # 1. Download ZIP
    downloader = IAZipDownloader()
    zip_path = await downloader.download_raw(tribunal, date)

    # 2. Transform
    transformer = DataTransformer()
    parquet_files = await transformer.transform(zip_path)

    # 3. Upload Parquet
    uploader = IAParquetUploader()
    for parquet_file in parquet_files:
        await uploader.upload(parquet_file, tribunal, date)

    return parquet_files
```

**New CLI commands**:
```bash
# Step 1: Scrape raw data → ZIP → IA
causaganha scrape --tribunal TJRO --days-back 7

# Step 2: Transform ZIP → Parquet → IA
causaganha transform --tribunal TJRO --date 2025-01-22

# Or combined workflow
causaganha scrape-and-transform --tribunal TJRO --days-back 7
```

---

## 📊 Code Audit Summary

| File | Purpose | Format | IA Upload | IA Download | Verdict |
|------|---------|--------|-----------|-------------|---------|
| `pipeline/collect.py` | Fetch PJe API → DuckDB | JSON | ❌ | ❌ | **REMOVE** (old architecture) |
| `pipeline/ia_download.py` | Download from IA | **Parquet** | ❌ | ✅ | Keep (needs ZIP support) |
| `pipeline/ia_upload.py` | Upload to IA | **Parquet** | ✅ | ❌ | Keep (needs ZIP support) |
| `pipeline/export_orchestrator.py` | DuckDB → Parquet → IA | **Parquet** | ✅ | ❌ | Keep (but after transform) |
| `api/client.py` | PJe API HTTP client | JSON | ❌ | ❌ | Keep if scraper uses it |

---

## ✅ Action Plan

### Phase 1: Verify New Scraper Exists
```bash
# Check if there's a separate scraping system
# (e.g., in another repo, cloud function, external service)
```

**If YES** → Go to Phase 2
**If NO** → Go to Phase 3

---

### Phase 2: Remove Old `collect` (Scraper exists elsewhere)

```bash
# 1. Delete old collection code
git rm src/causaganha/pipeline/collect.py

# 2. Remove CLI command
# Edit cli/__init__.py and remove @app.command() def collect(...)

# 3. Update tests (mark as deprecated or delete)
git rm tests/unit/test_pipeline_collect*.py
git rm tests/integration/test_pipeline_collect*.py

# 4. Update CLAUDE.md
# Remove references to "causaganha collect"

# 5. Commit
git commit -m "refactor: remove old collect command (replaced by external scraper)"
```

---

### Phase 3: Implement New ZIP-Based Scraper (Scraper does NOT exist)

**Tasks**:
1. Create `pipeline/scrape.py` (ZIP download logic)
2. Create `pipeline/transform.py` (ZIP → Parquet normalization)
3. Add ZIP support to `ia_download.py` and `ia_upload.py`
4. Update CLI with new commands: `scrape`, `transform`, `scrape-and-transform`
5. Write tests for new workflows
6. Document in CLAUDE.md

**Estimated effort**: 3-5 days

---

## 🎯 Recommended Decision

### **OPTION 1: REMOVE `collect` command**

**Reason**:
- Current `collect` does NOT match your described architecture (ZIP-based)
- It stores data locally in DuckDB (not IA-first)
- It's redundant if you have external scraper

**Impact**:
- Remove ~200 lines of code
- Simplify architecture
- Align with IA-first approach

**Verdict**: ✅ **RECOMMENDED** if scraper exists elsewhere

---

### **OPTION 2: REPLACE `collect` with new ZIP scraper**

**Reason**:
- No external scraper exists
- Need to implement ZIP → IA → Transform → Parquet workflow

**Impact**:
- Implement new scraping logic
- Add ZIP support to IA clients
- 3-5 days of work

**Verdict**: ⚠️ **Only if scraper doesn't exist**

---

## 📝 Final Answer

**Current state**:
- ❌ `collect` command does NOT download ZIP
- ❌ `collect` command does NOT upload to Internet Archive
- ❌ No ZIP support anywhere in codebase
- ✅ Only Parquet upload/download to/from IA exists

**Recommendation**:
- **If scraper exists elsewhere**: DELETE `pipeline/collect.py` and `causaganha collect` command
- **If scraper doesn't exist**: REPLACE with new ZIP-based scraper implementation

**Your question answered**:
> "Is this still in place? Does the `collect` command does anything like this?"

**Answer**: **NO**. The `collect` command does **NOT** do ZIP-based scraping. It's the old architecture (JSON → DuckDB). You can safely **remove it** if you have the new ZIP-based scraper elsewhere.

---

**Last Updated**: 2025-01-23
**Status**: 🚨 **Architecture Mismatch Identified**
