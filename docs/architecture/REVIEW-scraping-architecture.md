# Architecture Review: DJEN Scraping to Internet Archive

**Date:** 2026-02-12
**Scope:** End-to-end pipeline from DJEN API to permanent Internet Archive storage
**Instrumental Goal:** Reliable, complete scraping of DJEN data to Internet Archive

---

## Executive Summary

CausaGanha has a well-designed pipeline architecture with strong foundations:
immutable dataclasses, pure/impure boundary separation, catalog-driven backfill,
and parallel execution. However, there are several issues that directly threaten
the instrumental goal of reliably archiving DJEN data to the Internet Archive.

The most critical finding is a **missing authentication header in consolidation
uploads** (`consolidate.py:1441`), which means Parquet uploads to IA may be
silently failing. Additionally, there are **three competing IA upload
implementations** with no shared module, creating maintenance risk and
inconsistent behavior.

---

## 1. Critical Issues

### 1.1 Missing IA Authentication in Consolidation Uploads

**Severity: Critical** - Directly blocks the instrumental goal.

In `scripts/pipeline/consolidate.py:1441`, the upload client is created without
authorization:

```python
with httpx.Client(timeout=300) as client:
    # ...
    upload_to_ia(client, item_id, output_path, date_str)
```

Compare with `scripts/pipeline/collect.py:716`, which correctly injects auth:

```python
httpx.Client(
    timeout=upload_timeout,
    limits=pool_limits,
    headers={"Authorization": ia_auth},
) as upload_client,
```

The consolidation upload function (`consolidate.py:846`) sends the PUT request
via the shared client, but that client has **no `Authorization` header**. IA's
S3 API requires `Authorization: LOW access:secret`. This means consolidated
Parquet uploads are likely failing with 403 errors, getting swallowed by the
retry logic, and silently producing `uploaded: 0` in stats.

**Suggestion:** Add the same `_get_ia_s3_auth()` + header injection pattern
from `collect.py` to `consolidate.py`'s upload client creation.

### 1.2 Three Competing IA Upload Implementations

There are three distinct upload paths, violating DRY and creating divergence:

| Module | Method | Auth | Headers |
|--------|--------|------|---------|
| `scripts/pipeline/collect.py:499` | httpx PUT to S3 | `LOW key:secret` | `x-archive-meta-*` |
| `scripts/pipeline/consolidate.py:846` | httpx PUT to S3 | **MISSING** | `x-archive-meta-*` |
| `src/causaganha/pipeline/ia_upload.py:70` | `internetarchive` lib | `ia.configure()` | Library-managed |
| `src/causaganha/clients/archive.py:146` | `internetarchive` lib | `ia.get_session()` | Library-managed |

The `CONTRIBUTING.md` explicitly warns "Do not replace httpx with boto3" and
documents why `internetarchive`/`boto3` approaches fail (HTTP 411, wrong header
prefix). Yet two modules (`ia_upload.py`, `archive.py`) still use the
`internetarchive` library.

**Suggestion:** Extract a single `ia_s3.py` module with the httpx-based upload
logic, shared by both `collect.py` and `consolidate.py`. Deprecate or remove
the `internetarchive`-library-based implementations unless they serve a distinct
purpose (e.g., metadata queries vs uploads).

### 1.3 Item ID Naming Inconsistency

- `collect.py` and `consolidate.py`: `djen-{date}` (daily bucket, all tribunals)
- `ia_upload.py:256`: `djen-raw-{date}-{tribunal}` (per-tribunal bucket)

The `ia_upload.py` naming scheme creates separate IA items per tribunal per day,
which contradicts the established pattern of one IA item per day containing all
tribunals' files. If `ia_upload.py` is ever called in production, it would
scatter files across thousands of IA items instead of the daily buckets.

**Suggestion:** Align `ia_upload.py` to use `djen-{date}` or document that it
serves a different purpose.

---

## 2. Structural Issues

### 2.1 Duplicated Code Between collect.py and consolidate.py

Both scripts duplicate significant logic:

- `upload_to_ia()` - ~60 lines, nearly identical
- `_compute_md5()` - identical
- `parse_deadline()` - identical
- `download_zip()` - similar but with different signatures

This means bug fixes (like the auth issue above) must be applied in two places.
The consolidation upload already diverged (missing auth) precisely because of
this duplication.

**Suggestion:** Extract shared functions into a `pipeline/shared.py` or
`pipeline/ia_s3.py` module. Both scripts import from it. The functions to
extract:

```
ia_s3_auth() -> str
compute_md5(path) -> str
upload_to_ia(client, item_id, path, date, metadata) -> bool
parse_deadline(s) -> int
```

### 2.2 Duplicate Global Variable Declaration

`consolidate.py` declares `_TRIBUNAL_STOPPED_CACHE` twice (lines 60-61 and
63-64). The second declaration shadows the first. While functionally harmless
(both are `dict[str, dict[str, bool]]`), it signals copy-paste drift and
could confuse readers or static analyzers.

### 2.3 Module-Level Mutable State

`consolidate.py` uses module-level mutable globals:

```python
_TRIBUNAL_STOPPED_CACHE: dict[str, dict[str, bool]] = {}
_CONSOLIDATION_CANDIDATES: list[str] | None = None
```

This makes testing harder (state leaks between tests), prevents
parallelization, and creates implicit coupling. The pipeline orchestrator
(`run.py`) correctly uses frozen dataclasses, but the sub-scripts don't follow
the same pattern.

**Suggestion:** Encapsulate state into a `ConsolidationContext` class passed
through function arguments, matching the immutable style of `run.py`.

### 2.4 Two Collection Modules with Overlapping Names

- `src/causaganha/pipeline/collect.py` - Library-style async collection,
  stores to DuckDB, does NOT upload to IA
- `scripts/pipeline/collect.py` - Script-style collection, downloads ZIPs,
  uploads to IA

The library version is the older approach. The script version is the production
path. Having both creates confusion about which is canonical.

**Suggestion:** Either remove the library version or rename it to something
like `djen_client.py` to clarify it's a DJEN API client, not the production
collection pipeline.

---

## 3. Reliability Concerns for Scraping Goal

### 3.1 No Circuit Breaker for IA Operations

If Internet Archive is experiencing downtime (which happens), the system will:
1. Try each upload 3 times with backoff
2. Fail each item individually
3. Report many individual failures

With 96 tribunals per day, that's 96 x 3 = 288 failed requests before the
system gives up on a single date. There's no "IA seems down, stop trying"
logic.

**Suggestion:** Add a simple circuit breaker: after N consecutive IA failures
(e.g., 5), assume IA is down and skip remaining uploads for this run. Log the
circuit break event. The next pipeline run (5-10 minutes later) will retry.

```python
class CircuitBreaker:
    def __init__(self, threshold: int = 5):
        self.consecutive_failures = 0
        self.threshold = threshold

    def record_success(self):
        self.consecutive_failures = 0

    def record_failure(self):
        self.consecutive_failures += 1

    @property
    def is_open(self) -> bool:
        return self.consecutive_failures >= self.threshold
```

### 3.2 No Post-Upload Verification for Consolidation

`collect.py` sends `Content-MD5` headers which IA checks server-side. But after
upload, neither script verifies the file is actually accessible on IA. The
`ia_upload.py` library version has `_verify_upload()`, but the production
scripts don't.

For the instrumental goal of reliable archival, a lightweight HEAD request after
upload would catch:
- IA queueing delays (item created but file not yet available)
- Silent upload failures (200 response but file not stored)

**Suggestion:** After upload succeeds, do a `HEAD
https://archive.org/download/{item_id}/{filename}` with a short delay.
Not blocking, just informational logging.

### 3.3 Backfill Relies on Stale Catalog

The `collect.py` backfill queue comes from `backfill-needed.parquet`, which is
rebuilt only when the catalog step runs (conditionally, after other steps).
Between catalog rebuilds, the backfill list is stale. `collect.py` mitigates
this by checking IA directly for recently collected items, but this creates
redundant work:

1. Catalog says date X needs backfill
2. Collect downloads backfill list and checks IA
3. IA confirms date X was already collected (since last catalog build)
4. Collect skips it

This is correct but wasteful. Each "skip" still requires an IA metadata API
call.

**Suggestion:** The DuckDB-based `djen_state.coverage` table in `collect.py`
is the right optimization. Ensure it's the primary skip mechanism and IA
checks are only for uncached dates. The current implementation does this, but
the caching layer could be shared between collect and consolidate.

### 3.4 Consolidation Completeness Threshold

Consolidation waits for all 96 tribunals (or marks absent ones). But
`_is_tribunal_stopped()` uses a 60-day window, which means:

- A new tribunal added to the DJEN API will appear as "stopped" if it has no
  history
- A tribunal that goes offline for 59 days then comes back will be expected but
  absent, blocking consolidation for those dates

The logic is sound for steady-state operation, but edge cases around tribunal
lifecycle changes could block consolidation indefinitely.

**Suggestion:** Add a "force consolidation after N days waiting" policy. If a
date has been pending consolidation for >7 days and is >90% complete, force it
with whatever tribunals are available. Missing data can be backfilled later.

---

## 4. Performance Observations

### 4.1 Idle Pipeline is Well-Optimized

The BDD spec targets <20 seconds for idle runs, and the architecture supports
this through:
- DuckDB-based local coverage cache (avoids IA calls for known items)
- Catalog-driven backfill (no scanning when everything is current)
- Early exits when no work is needed

### 4.2 Memory Pressure During Consolidation

`consolidate_date()` loads all JSON from 96 ZIPs into NDJSON files, then loads
them into an in-memory DuckDB instance. For high-volume days (e.g., TJSP
alone can produce large volumes), this could stress GitHub Actions runner
memory (7GB limit).

The `workers: 2` setting in `run.py` is conservative, but the real pressure
comes from the DuckDB in-memory database holding all records simultaneously.

**Suggestion:** Consider streaming consolidation: process tribunals in batches
(e.g., 20 at a time) and append to the output Parquet files incrementally.
DuckDB supports `COPY ... TO ... (APPEND)` mode.

### 4.3 Parallel Upload Opportunity

`consolidate.py` uploads tables in parallel (4 workers), which is good. But
`collect.py` uploads sequentially within each worker thread (one file per
`_process_item` call). Since each worker handles one (date, tribunal) pair and
there's only one file per pair, this is fine. No change needed.

---

## 5. Architecture Strengths (Preserve These)

These design decisions are strong and should be maintained:

1. **Immutable pipeline state** (`run.py` frozen dataclasses) - Prevents
   subtle mutation bugs, makes state transitions auditable.

2. **Pure/impure boundary** - Core logic is testable without IO mocking.

3. **Catalog as single source of truth** - `manifest.parquet` on IA drives
   backfill, dashboard, and discovery. Eliminates need for a persistent DB.

4. **Daily IA items** (`djen-{date}`) - Clean, predictable URL scheme.
   DuckDB can query remote Parquets directly via HTTP range requests.

5. **httpx-based IA S3 uploads** - Correctly handles IA's non-standard
   requirements (`x-archive-meta-*` headers, explicit `Content-MD5`).

6. **UUIDv5 deterministic IDs** - Re-running consolidation produces identical
   UUIDs, making the pipeline idempotent.

7. **Absent markers** - `.absent` files complete the tribunal matrix without
   requiring actual data, enabling reliable completeness checks.

8. **BDD architecture specification** - `PIPELINE_ARCHITECTURE.feature`
   documents pipeline behavior as executable specifications.

---

## 6. Prioritized Recommendations

Ordered by impact on the instrumental goal (DJEN to IA archival):

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| P0 | Fix missing auth in consolidate.py uploads | Parquets not reaching IA | Small |
| P1 | Extract shared IA upload module | Prevents future auth/header divergence | Medium |
| P1 | Remove duplicate `_TRIBUNAL_STOPPED_CACHE` | Code hygiene | Trivial |
| P2 | Add circuit breaker for IA operations | Graceful degradation during IA outages | Small |
| P2 | Clarify or remove `ia_upload.py` / `archive.py` | Reduce confusion about which upload path is canonical | Medium |
| P3 | Add post-upload verification (HEAD check) | Catch silent upload failures | Small |
| P3 | Force-consolidate after N days waiting | Prevent indefinite blocking on incomplete days | Small |
| P3 | Encapsulate consolidation mutable state | Testability, matches run.py style | Medium |
| P4 | Rename/remove `src/.../pipeline/collect.py` | Eliminate naming confusion with script version | Small |
| P4 | Streaming consolidation for memory pressure | Prevent OOM on high-volume days | Large |

---

## 7. Data Flow Diagram (Current State)

```
                      DJEN API (96 courts, geo-blocked)
                              |
                              v
                    DJEN Proxy (Cloud Run, SP)
                              |
                              v
              +------ scripts/pipeline/collect.py ------+
              |   httpx GET -> ZIP download              |
              |   httpx PUT -> IA S3 (x-archive-meta-*)  |
              |   DuckDB local coverage cache            |
              +------------------------------------------+
                              |
                              v
                    Internet Archive (djen-{date}/)
                    ├── djen-{date}-TJSP.zip
                    ├── djen-{date}-TJRO.absent
                    └── ... (96 files)
                              |
                              v
           +------ scripts/pipeline/consolidate.py ------+
           |   Download ZIPs from IA                      |
           |   Extract JSON -> NDJSON (per tribunal)      |
           |   DuckDB + Ibis: normalize, deduplicate      |
           |   UUIDv5 for deterministic IDs               |
           |   Export 10 Parquet tables                    |
           |   httpx PUT -> IA S3 [AUTH MISSING!]         |
           +--------------------------------------------- +
                              |
                              v
                    Internet Archive (djen-{date}/)
                    ├── comunicacoes.parquet
                    ├── advogados.parquet
                    ├── textos.parquet
                    └── ... (10 Parquet tables)
                              |
                              v
           +------ scripts/generate_catalog.py -----------+
           |   Scan all djen-* items on IA                |
           |   Build manifest.parquet + backfill list     |
           |   Upload to causaganha-catalog item          |
           +----------------------------------------------+
                              |
                              v
                    Internet Archive (causaganha-catalog/)
                    ├── manifest.parquet
                    ├── backfill-needed.parquet
                    └── catalog.duckdb
```

---

## 8. Verification Commands

To check if the auth issue is actually causing failures, run:

```bash
# Check if any consolidation uploads have succeeded recently
python -c "
import duckdb
con = duckdb.connect()
con.execute('INSTALL httpfs; LOAD httpfs;')
result = con.execute(\"\"\"
    SELECT date, COUNT(*) as parquet_count
    FROM read_parquet('https://archive.org/download/causaganha-catalog/manifest.parquet')
    WHERE file_type = 'parquet'
    GROUP BY date
    ORDER BY date DESC
    LIMIT 10
\"\"\").fetchall()
for row in result:
    print(f'{row[0]}: {row[1]} parquets')
"
```

If this shows dates with ZIPs but no Parquets for recent dates, the auth issue
is confirmed.
