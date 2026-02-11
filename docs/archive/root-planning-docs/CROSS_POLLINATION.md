# causaganha ↔️ baliza Cross-Pollination Analysis

## Executive Summary

Both projects share the same DNA: scraping public APIs, storing in DuckDB, and archiving to the Internet Archive (IA). However, they optimize for different constraints. **causaganha** is built for **velocity and throughput**, utilizing parallel workers and lightweight uploaders to handle its massive 51k+ item backlog. **baliza** is built for **resilience and correctness**, with robust page-level checkpointing and structured state management, but currently suffers from sequential processing bottlenecks.

To meet the goal of accelerating `baliza`'s backfill, the primary action is porting `causaganha`'s concurrency model. Conversely, `causaganha` should mature its state management by adopting `baliza`'s database-centric approach.

## 🏆 causaganha Best Practices → baliza

### 1. Concurrent Worker Pool (The "Backfill Booster")
- **What**: Use `concurrent.futures.ThreadPoolExecutor` to process multiple days/units in parallel.
- **Why it matters**: `baliza` currently processes days sequentially. API latency dominates the runtime. Parallelizing completely changes the backfill velocity (e.g., 8x speedup with 8 workers).
- **Current baliza state**: Sequential processing in `extractor.py` (one date range loop).
- **Implementation task**: Refactor `baliza` CLI to accept a pool size and dispatch day-ranges to a thread pool, similar to `causaganha/scripts/pipeline/collect.py`.
- **Effort**: M
- **Files to change**: `src/baliza/cli_simple.py`, `src/baliza/extractor.py`

### 2. Lightweight S3 Uploader
- **What**: Direct `httpx` implementation for IA S3 API instead of the heavy `internetarchive` Python library.
- **Why it matters**: The `internetarchive` library performs many metadata checks and uses synchronous blocking calls. For a massive backfill, `causaganha`'s lightweight, low-level HTTP approach reduces overhead and plays better with async/threaded environments.
- **Current baliza state**: Uses `internetarchive` library in `upload_internet_archive.py`.
- **Implementation task**: Port `_get_ia_s3_auth` and `upload_to_ia` functions from `causaganha` to `baliza`.
- **Effort**: S
- **Files to change**: `scripts/upload_internet_archive.py`

### 3. Catalog-Driven Backfill
- **What**: A "missing items" catalog (Parquet/DB) that acts as the single source of truth for what needs to be collected, rather than just iterating date ranges.
- **Why it matters**: `causaganha` knows exactly which tribunal-dates are missing via `backfill-needed.parquet`. `baliza` relies on calculating ranges. A catalog allows for prioritized, gap-filling execution.
- **Current baliza state**: Date-range based extraction.
- **Implementation task**: Create a "coverage gap" query in `baliza` that feeds the new Concurrent Worker Pool.
- **Effort**: M
- **Files to change**: `src/baliza/extractor.py`

## 🏆 baliza Best Practices → causaganha

### 1. Unified State Management (DuckDB)
- **What**: Store collection state (what was downloaded/uploaded) in DuckDB tables (`djen_state.coverage`), not in a flat JSON file (`djen_cache.json`).
- **Why it matters**: `djen_cache.json` is a single point of failure, hard to query, and lacks concurrency safety (though `collect.py` tries to handle it). `baliza`'s relational state tracking is superior.
- **Current causaganha state**: `djen_cache.json` + `load_cache()`/`save_cache()`.
- **Implementation task**: Create `djen_state` schema and replace JSON cache logic with DuckDB queries.
- **Effort**: M
- **Files to change**: `scripts/pipeline/collect.py`

### 2. Granular Checkpointing
- **What**: Checkpoint progress *within* a unit of work. `baliza` saves state after every API page.
- **Why it matters**: If a `causaganha` worker fails during a long processing step (e.g., embedding generation), it starts over. Checkpointing allows resuming from the last successful "page" or "batch".
- **Current causaganha state**: Atomic file-level success/failure.
- **Implementation task**: Implement periodic state commits in `ExportOrchestrator` for long-running tasks.
- **Effort**: L
- **Files to change**: `src/causaganha/pipeline/export_orchestrator.py`

### 3. Input Sanitization & SSRF Protection
- **What**: Explicit `validate_url` and `validate_identifier` helpers.
- **Why it matters**: Security. `causaganha` trusts the config/env implicitly. `baliza` actively validates inputs.
- **Current causaganha state**: No explicit validation helpers found in `collect.py`.
- **Implementation task**: Port `utils.py` from `baliza` to `causaganha` and wrap inputs.
- **Effort**: S
- **Files to change**: `src/causaganha/utils.py` (new), `scripts/pipeline/collect.py`

## 📊 Side-by-Side Comparison Table

| Feature | causaganha | baliza | Winner | Action |
|---------|-----------|--------|--------|--------|
| **Concurrency** | 8 threads (`ThreadPoolExecutor`) | Sequential (Single loop) | **causaganha** | **URGENT: Port to baliza** |
| **State Storage** | `djen_cache.json` (Flat File) | DuckDB (`baliza_state` schema) | **baliza** | Port to causaganha |
| **IA Upload** | Direct `httpx` (Lightweight) | `internetarchive` lib (Heavy) | **causaganha** | Port to baliza (for speed) |
| **Checkpointing** | File-level (Atomic) | Page-level (Granular) | **baliza** | Keep as is (context dependent) |
| **Input Security** | Implicit Trust | `validate_url()` (Explicit) | **baliza** | Port to causaganha |
| **Backfill Logic** | Catalog-driven (Missing items) | Date-range driven | **causaganha** | Port "Gap Strategy" to baliza |

## 🎯 Priority Implementation Queue

1.  **[High Impact] Implement Concurrent Backfill in baliza**
    *   **Goal**: Enable `baliza` to scrape/upload 8 days simultaneously.
    *   **Task**: Refactor `baliza/cli_simple.py` to use `ThreadPoolExecutor` targeting `PNCPExtractor.extract` for single days.
    *   **Effort**: Medium

2.  **[High Stability] Migrate causaganha cache to DuckDB**
    *   **Goal**: Remove `djen_cache.json` and race conditions.
    *   **Task**: Introduce `djen_state.downloads` table in `collect.py`.
    *   **Effort**: Medium

3.  **[Performance] Switch baliza to Lightweight Uploader**
    *   **Goal**: Reduce overhead during massive backfills.
    *   **Task**: Replace `internetarchive` dependency with `httpx` put in `baliza`.
    *   **Effort**: Small

4.  **[Security] Add Input Validation to causaganha**
    *   **Goal**: Prevent SSRF/Injection.
    *   **Task**: Copy `validate_url` patterns.
    *   **Effort**: Small

## 🔧 Technical Implementation Notes

*   **DuckDB Concurrency**: When implementing parallel workers in `baliza`, ensure each worker uses its own DuckDB connection (cursor) or that the write lock is managed correctly. `causaganha`'s `collect.py` uses `ThreadPoolExecutor` but `djen_cache.json` is a critical section (though currently handled by "load-modify-save" which has race conditions—moving to DuckDB actually *solves* this if using a single writer or WAL).
*   **Rate Limits**: `baliza`'s API (PNCP) may have different rate limits than DJEN. `causaganha` handles 429s/500s with exponential backoff. Ensure the new parallel `baliza` implementation includes `tenacity` or manual backoff loops for *each* worker.
