# CLAUDE.md

Project guide for Claude Code. Keep this file short and actionable.

## What this repo is

CausaGanha archives Brazilian judicial communications (DJEN) on Internet Archive and serves a public dashboard. Two runtime surfaces:

- **Python backend** in `src/causaganha` and `src/djen_backup`
- **Web frontend** in `web/`: a static, zero-backend public reader (plain HTML/JS in `web/public/`, no build step). See `web/README.md`.
- **Agent Operating Manual** in `AGENTS.md` (detailed architectural invariants, active learning flywheel, and jurimetrics rules)

## Architecture at a glance

### djen-backup (sync engine)

**Accepted strategy, operational integration merged:** [ADR 0012](docs/adr/0012-acervo-inventariado-no-internet-archive.md). Rebuild the physical archive inventory from Internet Archive APIs. Consolidate available ZIPs per tribunal/partition without nationwide daily completeness. A missing ZIP is an unknown gap, not evidence of no publication. Preserve verification events to reconstruct collection status. Distinguish preserved, converted and searchable coverage. The “single source of truth” below refers to collection state, not the physical archive inventory. The tribunal/year workflow is integrated; use the rollout guide for publication evidence and remaining coverage, never infer full backlog completion from deployment.

The canonical sync engine is in `src/djen_backup/`. Key concepts:

- **`sync-manifest.parquet`** on IA (`https://archive.org/download/causaganha-dashboard/sync-manifest.parquet`) is the single source of truth. One row per `(tribunal, date)` pair with `ia_status`, `djen_status`, `djen_raw`, `updated_at`. It is the compacted base of an append-only event log (`manifest-log/*.csv` segments, absorbed by `scripts/render_manifest_parquet.py`) — see `docs/planning/manifest-source-of-truth.md`. The legacy `sync-manifest.csv` is retired as a source; it can still be produced as a derived export on demand (`MANIFEST_COMPACT_WRITEBACK=1` when running the compactor), but nothing reads it as canonical anymore.
- **`djen_raw`** stores the actual DJEN **HTTP status** ("200", "404", "400", "403", "timeout", "network"). It is the transport code, **not** a verdict on availability — in particular `djen_raw="200"` does **NOT** mean the caderno exists (see next bullet). Derive `djen_status` from the full response (status + body), and once derived, trust `djen_status` — not a bare reading of `djen_raw`.
- **A `200` can still be genuinely absent.** When there is no publication, DJEN returns HTTP **200 with body `{"status": "Sem comunicações"}`** (no download URL). `get_caderno_url` correctly raises `DJENNotFoundError(status_code=200)` for this. So **availability = HTTP 200 *and* a download URL in the body**; a 200-without-URL is `absent`, exactly like a 404. Do not equate `djen_raw="200"` with `djen_status="available"`.
- Engine runs 3 independent worker pools: **checkers** (DJEN API), **downloaders** (fetch ZIP), **uploaders** (push to IA).
- Periodic IA upload every 10 min protects against crashes.
- Phase 0 uses IA advanced search to discover existing items, then fetches metadata in parallel (~50 concurrent).
- **IA item naming**: Items use `djen-{tribunal}-{year}` format (e.g. `djen-tjro-2025`). The old `djen-YYYY-MM-DD` per-day format is discontinued. ZIP files inside items still use `djen-YYYY-MM-DD-{TRIBUNAL}.zip`.

### Lookup by CNJ vs. analytics

**Proposed:** [ADR 0013](docs/adr/0013-indice-protobuf-por-cnj-sobre-originais.md). The original DJEN/DataJud ZIPs on IA are canonical; per-CNJ lookup goes through a Protobuf pointer index (item → ZIP → member) and returns the original bytes. Parquet stays as the analytics layer (jurimetria, catalog SQL, DuckDB scans), not as a CNJ index. Don't add a second canonical encoding of document content.

### Manifest query contracts (web)

`.qmd` contracts in `web/queries/` declare analytical datasets. Each has YAML frontmatter (`output: /data/foo.json`, `format: array|object`, optional `optional: true`) and a SQL block. `scripts/render_queries.py` executes them against the manifest and writes JSON to `web/public/data/` (the deploy workflow runs it with `--strict`).

**Consumers:** `web/public/index.html` does not currently fetch `/data/*.json`. It reads `indexes/*.json`, shards via HTTP Range requests, `catalogo_tpu.json`, and DJEN parquet through DuckDB-WASM httpfs (via `djen-proxy`). Confirm a page consumes a contract before assuming it is shown.

**Adding a dataset:** add a `.qmd` to `web/queries/`, validate with `uv run python scripts/render_queries.py --check`, then wire the JSON into a page by hand (there is no Zod registry or `loadContract` any more).

## Running things

```bash
# Full sync (check DJEN + download + upload)
uv run --env-file ~/workspace/.env djen-backup --workers 8

# Only check DJEN availability (no I/O)
uv run --env-file ~/workspace/.env djen-backup check --workers 8

# Only upload already-available entries
uv run --env-file ~/workspace/.env djen-backup upload --workers 4

# Render query contracts to JSON
uv run python scripts/render_queries.py

# Preview the static site (no build step; serve over HTTP, not file://)
# Note: python's http.server ignores Range requests, which shard lookups need.
python3 -m http.server -d web/public 8000
```

## Rules of the road

### Correctness

- **Never treat 403 as absent.** CloudFront/WAF returns 403 when rate-limiting. Genuine absent is: **404**, **400** (holidays), **or 200 with body `"Sem comunicações"`** (no download URL). A bare 200 status is *not* enough to call it available.
- **`djen_raw="200"` + `djen_status="available"` is NOT self-consistent proof — historically.** ~79K legacy rows were recorded by an older checker that read only the HTTP 200 and never inspected the body — they were actually "Sem comunicações" (absent). This was fixed by promoting the corrected `sync-manifest.parquet` (built from the probe **upload-delta** corrections) to the sole source of truth (see `docs/planning/manifest-source-of-truth.md` Fase 1); the legacy `sync-manifest.csv` was never backfilled and is no longer read by anything (Fase 3). Before "fixing" any available/absent discrepancy you find elsewhere, **verify against live DJEN** (sample → `get_caderno_url`) — do not assume a recorded status is right just because it looks canonical.
- **Don't trust `absent` from old runs.** If auditing shows false positives, reset all `absent` entries (where `djen_raw` is empty) to unknown.
- **Upload bodies are streamed, never fully buffered.** `causaganha.pipeline.ia_s3._perform_upload` streams the file via `_FileChunkStream` (16 MiB chunks) with an explicit `Content-Length`, building a fresh body per attempt so retries and 307 redirects resend the whole file. Don't pass a sync file object as `content=` (fails under `AsyncClient`), don't use a one-shot async generator (`StreamConsumed` on redirect), and don't go back to `read_bytes()` — consolidate parquets are 2-3 GB. Transient `OSError`s are retried; `FileNotFoundError`/`PermissionError`/`IsADirectoryError` are not.
- **Per-item lock + token bucket for IA uploads** (in `src/djen_backup/archive.py`). IA serializes writes per item. `ItemBusyError` → re-queue, don't block.

### Performance

- Rate-limit observer updates (`_notify_counts` throttled to 2Hz) — `manifest.counts()` scans 157K entries; calling it per mark is an event-loop killer.
- Cache `has_uploaded_entries` / `counts` in `SyncManifest`; invalidate on mutation.
- For sampling/debugging absent entries, see patterns in previous audit (sample → `get_caderno_url` live).

### Static page styling

`web/public/index.html` is a single self-contained page: styling is one inline `<style>` block with `:root` custom properties.

### Style

- Ruff is strict. Only formatter-incompatible ignores + accepted-pattern ignores are in `ruff.toml` (see comments).
- **No blind `except Exception`.** Use specific types: `httpx.HTTPError`, `httpx.RequestError`, `OSError`, `RuntimeError`. Exception: a per-item bulkhead inside a worker-pool loop over independent units of work (one upload, one LLM call, one table export) may catch `Exception` broadly *if* the handler calls `.exception(...)` (full traceback, never swallowed silently) before recording a per-item failure or re-raising — see `docs/adr/0011-broad-except-in-worker-loop-bulkheads.md`. This is not a license to catch broadly elsewhere; a new site must cite the ADR in a comment or use specific types.
- **TRY300/TRY301/TRY401 enforced.** Extract raises to inner functions.
- Python 3.12+, `|` unions, `from __future__ import annotations` at top.

## File map

```
src/djen_backup/
├── engine.py      — run_pipeline, checker/downloader/uploader workers
├── manifest.py    — SyncManifest (parquet+segment persistence, counts cache)
├── djen.py        — DJEN API client (get_caderno_url, download_zip)
├── archive.py     — IA upload (upload_zip, CircuitBreaker, per-item locks, TokenBucket)
├── retry.py       — HTTP retry with backoff
└── __main__.py    — Cyclopts CLI (full sync, check, upload subcommands)

scripts/
├── render_queries.py              — .qmd → JSON
└── generate_cache_from_manifest.py — legacy cache (kept during migration)

web/
├── README.md              — static reader architecture (zero-backend)
├── public/                — deployed as-is to GitHub Pages (index.html, auditoria.html, indexes/, shards/, tiles/, ...)
└── queries/               — .qmd contracts (see web/queries/README.md)
    ├── totals.qmd, datajud_totals.qmd, stj_totals.qmd, juris_totals.qmd
    ├── tribunal_coverage.qmd, tribunal_calendar.qmd, stats_coverage.qmd
    ├── daily_uploads.qmd, weekly_pattern.qmd, consolidation_status.qmd
    ├── court_reliability.qmd, lawyer_leaderboard.qmd, site_status.qmd
    ├── datajud_classes.qmd, juris_classes.qmd, juris_orgaos.qmd
    ├── processos_multi_fonte.qmd, stj_temas.qmd, stj_relatores.qmd
    └── README.md          — contract syntax
```

## Before committing

```bash
uv run ruff check
uv run ruff format --check
uv run pytest -q
```

## What NOT to do

- Don't use `boto3` for IA uploads. Use `httpx`. (IA needs `x-archive-meta-*` headers, not `x-amz-meta-*`.)
- Don't remove the per-item lock in `archive.py` — IA needs serialization per yearly bucket.
- Don't `mark_djen_raw` with a derived category ("absent"/"available") — always store the raw code.
- Don't generate cache JSONs from random sources. Canonical source is the manifest; use `.qmd` query contracts.
- Don't catch `Exception` broadly — be specific or it won't pass ruff (BLE001).
