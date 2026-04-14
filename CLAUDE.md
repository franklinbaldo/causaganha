# CLAUDE.md

Project guide for Claude Code. Keep this file short and actionable.

## What this repo is

CausaGanha archives Brazilian judicial communications (DJEN) on Internet Archive and serves a public dashboard. Two runtime surfaces:

- **Python backend** in `src/causaganha` and `src/djen_backup`
- **Web frontend** in `web/` (Astro 5 + Svelte 5)

## Architecture at a glance

### djen-backup (sync engine)

The canonical sync engine is in `src/djen_backup/`. Key concepts:

- **`sync-manifest.csv`** on IA (`https://archive.org/download/causaganha-dashboard/sync-manifest.csv`) is the single source of truth. One row per `(tribunal, date)` pair with `ia_status`, `djen_status`, `djen_raw`, `updated_at`.
- **`djen_raw`** stores the actual DJEN response ("200", "404", "400", "403", "timeout", "network"). Never derive absent from just a category — always trust the raw.
- Engine runs 3 independent worker pools: **checkers** (DJEN API), **downloaders** (fetch ZIP), **uploaders** (push to IA).
- Periodic IA upload every 10 min protects against crashes.
- Phase 0 uses IA advanced search to discover existing items, then fetches metadata in parallel (~50 concurrent).

### Manifest query contracts (web)

The frontend declares its data needs via `.qmd` files in `web/src/queries/`. Each has YAML frontmatter (`output: /data/foo.json`, `format: array|object`) and a SQL block. Backend script `scripts/render_queries.py` executes them against the manifest and writes JSON to `web/public/data/`.

**When frontend needs a new dataset:** add a `.qmd`, add a typed loader in `web/src/lib/queryData.ts`, done. Python backend doesn't care.

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

# Frontend dev
cd web && npm run dev
```

## Rules of the road

### Correctness

- **Never treat 403 as absent.** CloudFront/WAF returns 403 when rate-limiting. Only 404 (+ 400 for holidays) is genuine absent.
- **Don't trust `absent` from old runs.** If auditing shows false positives, reset all `absent` entries (where `djen_raw` is empty) to unknown.
- **Upload bug:** `ia_s3._perform_upload` must use `file_path.read_bytes()`, not `file_path.open("rb")` as content — sync file objects don't work with `AsyncClient`.
- **Per-item lock + token bucket for IA uploads** (in `src/djen_backup/archive.py`). IA serializes writes per item. `ItemBusyError` → re-queue, don't block.

### Performance

- Rate-limit observer updates (`_notify_counts` throttled to 2Hz) — `manifest.counts()` scans 157K entries; calling it per mark is an event-loop killer.
- Cache `has_uploaded_entries` / `counts` in `SyncManifest`; invalidate on mutation.
- For sampling/debugging absent entries, see patterns in previous audit (sample → `get_caderno_url` live).

### Style

- Ruff is strict. Only formatter-incompatible ignores + accepted-pattern ignores are in `ruff.toml` (see comments).
- **No blind `except Exception`.** Use specific types: `httpx.HTTPError`, `httpx.RequestError`, `OSError`, `RuntimeError`.
- **TRY300/TRY301/TRY401 enforced.** Extract raises to inner functions.
- Python 3.12+, `|` unions, `from __future__ import annotations` at top.

## File map

```
src/djen_backup/
├── engine.py      — run_pipeline, checker/downloader/uploader workers
├── manifest.py    — SyncManifest (CSV persistence, counts cache)
├── djen.py        — DJEN API client (get_caderno_url, download_zip)
├── archive.py     — IA upload (upload_zip, CircuitBreaker, per-item locks, TokenBucket)
├── retry.py       — HTTP retry with backoff
└── __main__.py    — Typer CLI (full sync, check, upload subcommands)

scripts/
├── render_queries.py              — .qmd → JSON
└── generate_cache_from_manifest.py — legacy cache (kept during migration)

web/src/queries/
├── README.md              — query contract docs
├── totals.qmd             — overall counts
├── tribunal_coverage.qmd  — per-tribunal coverage
└── daily_uploads.qmd      — velocity/heatmap input
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
