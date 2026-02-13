# Task: Fix DJEN-to-Internet Archive Scraping Architecture

## Context

CausaGanha is a judicial analytics platform that scrapes Brazil's DJEN (Diário de Justiça Eletrônico Nacional) and archives the data permanently on Internet Archive. An architecture review identified 6 verified issues that threaten the reliability of this archival pipeline. All issues have been confirmed to exist in the current code.

The full review is at `docs/architecture/REVIEW-scraping-architecture.md`.

## Issues to Fix (in priority order)

### P0: Missing IA authentication in consolidate.py uploads

**File:** `scripts/pipeline/consolidate.py`
**Problem:** Line 1441 creates `httpx.Client(timeout=300)` with NO Authorization header. The Internet Archive S3 API requires `Authorization: LOW access:secret`. This means all Parquet uploads from consolidation are silently failing with 403.
**Reference implementation:** `scripts/pipeline/collect.py` lines 472-487 (`_get_ia_s3_auth()`) and line 716 (header injection).
**Fix:** The auth resolution logic needs to exist in consolidate.py and be injected into the upload client. But DON'T just copy-paste — this leads directly into P1.

### P1: Extract shared IA upload module (DRY)

**Problem:** 4 functions are duplicated across `scripts/pipeline/collect.py` and `scripts/pipeline/consolidate.py`:
- `upload_to_ia()` (~60 lines each, nearly identical but collect.py has auth and consolidate.py doesn't)
- `_compute_md5()` (identical)
- `parse_deadline()` (identical)
- `download_zip()` (similar signatures, both do httpx streaming with retry)

Additionally `scripts/pipeline/convert.py` has its own `download_zip()`.

**Fix:** Create `scripts/pipeline/ia_s3.py` containing:
- `get_ia_s3_auth() -> str | None` — resolve credentials from env vars or ia.ini
- `compute_md5(file_path: Path) -> str` — hex-encoded MD5
- `upload_to_ia(client: httpx.Client, item_id: str, file_path: Path, date_str: str, metadata_overrides: dict | None = None) -> bool` — the canonical upload function with x-archive-meta-* headers, retry, and backoff
- `parse_deadline(duration_str: str) -> int` — parse "10m"/"600s" to seconds
- `create_upload_client(auth: str, timeout: int = 300, max_connections: int = 10) -> httpx.Client` — factory that creates a properly configured client WITH auth headers

Then refactor both `collect.py` and `consolidate.py` to import from `ia_s3.py` instead of defining their own versions. Remove the duplicated functions from both files.

For `download_zip`, keep the script-specific versions since their signatures differ (collect.py takes a client + URL, consolidate.py takes item_id + filename), but extract the shared retry logic if possible.

### P1: Remove duplicate `_TRIBUNAL_STOPPED_CACHE` declaration

**File:** `scripts/pipeline/consolidate.py` lines 60 and 64
**Problem:** The variable `_TRIBUNAL_STOPPED_CACHE: dict[str, dict[str, bool]] = {}` is declared twice. Delete one.

### P2: Add circuit breaker for IA operations

**Problem:** If Internet Archive is down, the system tries every upload 3x before failing. With 96 tribunals, that's 288 wasted requests. No global "IA is down, stop trying" logic.

**Fix:** Add a simple `CircuitBreaker` class to `scripts/pipeline/ia_s3.py`:
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

Integrate it into `upload_to_ia()`: before attempting upload, check `if circuit_breaker.is_open: return False`. After success/failure, call `record_success()`/`record_failure()`. The circuit breaker should be an optional parameter (default None = no circuit breaking, for backward compat).

### P2: Clarify or deprecate `internetarchive`-library-based upload modules

**Files:**
- `src/causaganha/pipeline/ia_upload.py` — uses `internetarchive` lib (`ia.get_item().upload()`)
- `src/causaganha/clients/archive.py` — uses `internetarchive` lib (`ia.get_session()`)

**Problem:** `CONTRIBUTING.md` explicitly says "Do not replace httpx with boto3 for IA uploads" because IA requires `x-archive-meta-*` headers. The `internetarchive` Python library has the same issues. These modules are NOT used by the production pipeline (which uses the httpx-based scripts), creating confusion.

**Fix:** Add deprecation warnings at the top of both files pointing to `scripts/pipeline/ia_s3.py` as the canonical upload path. Add a comment in each class explaining the module is kept only for metadata queries / download operations (if that's true), not for uploads.

Also fix the item ID in `ia_upload.py:256`: it generates `djen-raw-{date}-{tribunal}` but production uses `djen-{date}`. Either align it or document clearly that this module is not for production use.

### P3: Encapsulate consolidation mutable state

**File:** `scripts/pipeline/consolidate.py`
**Problem:** Module-level mutable globals (`_TRIBUNAL_STOPPED_CACHE`, `_CONSOLIDATION_CANDIDATES`) make testing hard and create implicit coupling.
**Fix:** Create a `ConsolidationContext` dataclass that holds these caches, passed through function parameters. This matches the immutable style of `scripts/pipeline/run.py`.

## Constraints

- **DO NOT use boto3 or change the httpx-based upload approach** — see CONTRIBUTING.md
- **DO NOT change the IA item naming scheme** (`djen-{date}`) for production scripts
- **Preserve the `x-archive-meta-*` header format** — IA requires this, not `x-amz-meta-*`
- **Run `ruff check` and `ruff format`** after changes — the project uses ruff for linting
- **Run tests with `pytest`** after changes to check for regressions
- **Keep the frozen dataclass pattern** from `run.py` where applicable

## Verification

After implementing, verify:
1. `ruff check src/ scripts/` passes
2. `pytest` passes
3. `grep -r "def upload_to_ia" scripts/pipeline/` shows only ONE definition (in ia_s3.py), not three
4. `grep -r "def _compute_md5" scripts/pipeline/` shows only ONE definition
5. `grep -r "Authorization" scripts/pipeline/consolidate.py` shows the auth is being used (via import from ia_s3.py)
6. `grep -c "_TRIBUNAL_STOPPED_CACHE" scripts/pipeline/consolidate.py` for the duplicate declaration is gone (should have exactly one declaration)

## Commit Strategy

Make separate commits for each priority level:
1. `fix: add missing IA auth to consolidate.py uploads` (P0 — can be a quick fix before the refactor)
2. `refactor: extract shared IA S3 upload module` (P1 — the big DRY refactor)
3. `fix: add circuit breaker for IA upload operations` (P2)
4. `refactor: deprecate internetarchive-lib upload modules` (P2)
5. `refactor: encapsulate consolidation mutable state` (P3)

Push all commits to the working branch when done.
