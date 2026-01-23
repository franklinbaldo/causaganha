# 🗑️ PDF Code Removal Plan

## Context

**User request**: "We don't need pdf anymore, if we still have code about pdf we can delete the code"

**Current state**: CausaGanha has migrated to **texto-based analysis** (using the `texto` field from PJe API) instead of downloading and analyzing PDF files.

---

## 📊 PDF Code Audit

### Files with PDF Code

| File | PDF Code | Can Delete? | Action |
|------|----------|-------------|--------|
| `analysis/analyzer.py` | `analyze_pdf()` method (DEPRECATED) | ⚠️ Partial | Remove method, keep `analyze_text()` |
| `analysis/hybrid_analyzer.py` | `pdf_url` parameters (unused) | ⚠️ Partial | Remove `pdf_url` params |
| `pipeline/analyze.py` | Comments about PDFs | ⚠️ Partial | Clean up comments |
| `pipeline/archive.py` | **Downloads PDFs to IA** | ❓ | Keep or delete? (see below) |
| `clients/document.py` | `download_pdf()` method | ✅ Yes | **DELETE FILE** |
| `clients/preservation.py` | Uses `download_pdf()` | ✅ Yes | **DELETE FILE** |
| `clients/archive.py` | PDF archiving service | ⚠️ Partial | Keep IA upload, remove PDF-specific code |

**Total references**: 41 across src/ and tests/

---

## 🎯 Decision: Archive Pipeline

### Current `pipeline/archive.py` Flow

```
1. Get unarchived intimations from DuckDB
2. Download PDF from intimation.link (PJe URL)
3. Upload PDF to Internet Archive
4. Store IA URL in intimations.ia_url
```

### Question: Do we still need this?

**Arguments for KEEPING**:
- ✅ Preserves original documents for historical record
- ✅ Provides public access to source documents
- ✅ Independent of analysis (archival is separate concern)

**Arguments for DELETING**:
- ❌ PDFs not needed for analysis (using `texto` field)
- ❌ Storage costs (PDFs are large)
- ❌ Adds complexity to pipeline

**Recommendation**: **DELETE** unless you need historical preservation.

---

## 🗑️ Removal Plan

### Phase 1: Remove PDF Analysis Code

#### 1.1 Remove `analyze_pdf()` from `analysis/analyzer.py`

```python
# DELETE THIS METHOD:
async def analyze_pdf(
    self,
    pdf_url: str,
    intimation_id: int | None = None,
) -> DecisionAnalysis:
    """Analyze a single PDF decision document."""
    # ... (entire method)
```

**Impact**:
- ✅ No breaking changes (method already deprecated)
- ✅ All code uses `analyze_text()` now

---

#### 1.2 Remove `pdf_url` parameters from `hybrid_analyzer.py`

```python
# BEFORE:
async def analyze_text(
    self,
    text: str,
    intimation_id: int | None = None,
    pdf_url: str | None = None,  # ← DELETE THIS
) -> DecisionAnalysis:

# AFTER:
async def analyze_text(
    self,
    text: str,
    intimation_id: int | None = None,
) -> DecisionAnalysis:
```

```python
# BEFORE:
async def analyze_batch(
    self,
    texts: list[str],
    intimation_ids: list[int],
    pdf_urls: list[str | None] | None = None,  # ← DELETE THIS
) -> list[DecisionAnalysis | Exception]:

# AFTER:
async def analyze_batch(
    self,
    texts: list[str],
    intimation_ids: list[int],
) -> list[DecisionAnalysis | Exception]:
```

**Impact**:
- ✅ Simplifies interface
- ✅ All callers pass `pdf_urls=None` anyway (unused)

---

#### 1.3 Clean up `pipeline/analyze.py`

Remove PDF-related comments:

```python
# DELETE THESE COMMENTS:
"""PDF analysis pipeline with RAG and LLM support."""
# LLM now uses texto (no PDF needed!)
# Hybrid uses texto for both RAG and LLM fallback (no PDF!)
pdf_urls=None,  # No PDFs needed anymore!

# REPLACE WITH:
"""Decision analysis pipeline with RAG and LLM support."""
# Uses texto field for analysis
```

---

### Phase 2: Delete PDF Download/Archive Code

#### 2.1 Delete `clients/document.py`

**File**: `src/causaganha/clients/document.py`

```bash
git rm src/causaganha/clients/document.py
```

**Reason**: Only contains `download_pdf()` method, not used anymore.

---

#### 2.2 Delete `clients/preservation.py`

**File**: `src/causaganha/clients/preservation.py`

```bash
git rm src/causaganha/clients/preservation.py
```

**Reason**: Orchestrates PDF download + IA upload, not needed.

---

#### 2.3 Delete or Simplify `clients/archive.py`

**Option A: Keep IA upload functionality** (for Parquet files)
- Remove PDF-specific metadata
- Keep generic IA upload methods

**Option B: Delete entirely**
- If only used by archive pipeline (which we're deleting)

**Recommendation**: Keep simplified version for Parquet uploads.

---

#### 2.4 Delete `pipeline/archive.py`

**File**: `src/causaganha/pipeline/archive.py`

```bash
git rm src/causaganha/pipeline/archive.py
```

**Reason**: Downloads PDFs and uploads to IA, not needed.

**Impact**:
- ❌ Removes `causaganha archive` command
- ❌ Removes PDF preservation to Internet Archive
- ✅ Simplifies pipeline (collect → analyze → score → export)

---

### Phase 3: Remove CLI Command

#### 3.1 Remove `archive` command from CLI

```python
# cli/__init__.py

# DELETE THIS:
@app.command()
def archive(
    limit: int = typer.Option(10, help="Max intimations to archive"),
    dry_run: bool = typer.Option(False, help="Don't upload, just test"),
):
    """Download and archive documents to Internet Archive."""
    # ...
```

---

### Phase 4: Update Tests

#### 4.1 Delete PDF-related tests

```bash
# Find and delete
git rm tests/unit/test_document_service.py
git rm tests/unit/test_preservation.py
git rm tests/unit/test_archive_pipeline.py
git rm tests/integration/test_archive_pipeline.py

# Or mark as deprecated
@pytest.mark.skip(reason="PDF functionality removed")
```

---

### Phase 5: Update Documentation

#### 5.1 Update `CLAUDE.md`

Remove references to:
- `causaganha archive` command
- PDF download/analysis
- Document archiving

#### 5.2 Update `ARCHITECTURE_EXPLAINED.md`

Remove:
- Step 2: ARCHIVE (Download PDFs → Internet Archive)
- Update pipeline to: collect → analyze → score → export

#### 5.3 Update `TEXTO_VS_PDF_CLARIFICATION.md`

Add note:
> "✅ **UPDATE 2025-01-23**: PDF download and analysis code has been completely removed. All analysis now uses the `texto` field exclusively."

---

## 📋 Execution Checklist

### ✅ Phase 1: Clean Analysis Code
- [ ] Remove `analyze_pdf()` from `analysis/analyzer.py`
- [ ] Remove `pdf_url` params from `analysis/hybrid_analyzer.py`
- [ ] Clean up comments in `pipeline/analyze.py`
- [ ] Clean up comments in `pipeline/analyze_parquet.py`

### ✅ Phase 2: Delete PDF Files
- [ ] Delete `clients/document.py`
- [ ] Delete `clients/preservation.py`
- [ ] Delete `pipeline/archive.py`
- [ ] Simplify `clients/archive.py` (keep IA upload for Parquet)

### ✅ Phase 3: Update CLI
- [ ] Remove `archive` command from `cli/__init__.py`

### ✅ Phase 4: Update Tests
- [ ] Delete/skip PDF-related tests

### ✅ Phase 5: Update Documentation
- [ ] Update `CLAUDE.md`
- [ ] Update `ARCHITECTURE_EXPLAINED.md`
- [ ] Update `TEXTO_VS_PDF_CLARIFICATION.md`

---

## 💾 Estimated Impact

### Lines of Code Removed
```
clients/document.py:         ~200 lines
clients/preservation.py:     ~150 lines
pipeline/archive.py:         ~120 lines
analysis/analyzer.py:        ~50 lines (analyze_pdf method)
analysis/hybrid_analyzer.py: ~20 lines (pdf_url params)
CLI command:                 ~30 lines
Tests:                       ~300 lines

Total:                       ~870 lines deleted
```

### Files Deleted
```
src/causaganha/clients/document.py
src/causaganha/clients/preservation.py
src/causaganha/pipeline/archive.py
tests/unit/test_document_service.py
tests/unit/test_preservation.py
tests/unit/test_archive_pipeline.py
tests/integration/test_archive_pipeline.py

Total: 7 files deleted
```

### Commands Removed
```
causaganha archive
```

### New Pipeline (Simplified)
```
BEFORE: collect → archive → analyze → score → export
                   ^^^^^^^ REMOVED

AFTER:  collect → analyze → score → export
        ^^^^^^^ (also needs removal, see SCRAPING_ANALYSIS.md)

FINAL:  scrape → transform → analyze → score → export
```

---

## ⚠️ Breaking Changes

### External Systems
- ❌ `intimations.ia_url` field will no longer be populated
- ❌ PDF archiving to Internet Archive will stop
- ❌ `causaganha archive` command will be removed

### Code Dependencies
- ✅ No breaking changes (all code already uses `texto` field)
- ✅ `analyze_pdf()` was already deprecated
- ✅ All analysis methods work without PDFs

---

## 🎯 Recommendation

**Execute removal in 3 commits**:

1. **Commit 1: Clean analysis code** (safe, no breaking changes)
   - Remove `analyze_pdf()` method
   - Remove `pdf_url` parameters
   - Clean up comments

2. **Commit 2: Delete PDF infrastructure** (breaking, but unused)
   - Delete `document.py`, `preservation.py`, `archive.py`
   - Remove `archive` CLI command

3. **Commit 3: Clean up tests and docs**
   - Delete PDF tests
   - Update documentation

---

**Status**: ⏳ Ready for execution
**Estimated time**: 1-2 hours
**Risk level**: 🟢 Low (PDF code already deprecated/unused)
