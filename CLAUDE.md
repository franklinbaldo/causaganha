# CLAUDE.md

Project guide for Claude Code. Keep this file short and actionable.

## What this repo is

CausaGanha archives Brazilian judicial communications (DJEN) on Internet Archive and serves a public dashboard. Two runtime surfaces:

- **Python backend** in `src/causaganha` and `src/djen_backup`
- **Web frontend** in `web/` (Astro 5 + Svelte 5)

## Architecture at a glance

### djen-backup (sync engine)

The canonical sync engine is in `src/djen_backup/`. Key concepts:

- **`sync-manifest.parquet`** on IA (`https://archive.org/download/causaganha-dashboard/sync-manifest.parquet`) is the single source of truth. One row per `(tribunal, date)` pair with `ia_status`, `djen_status`, `djen_raw`, `updated_at`. It is the compacted base of an append-only event log (`manifest-log/*.csv` segments, absorbed by `scripts/render_manifest_parquet.py`) — see `docs/planning/manifest-source-of-truth.md`. The legacy `sync-manifest.csv` is retired as a source; it can still be produced as a derived export on demand (`MANIFEST_COMPACT_WRITEBACK=1` when running the compactor), but nothing reads it as canonical anymore.
- **`djen_raw`** stores the actual DJEN **HTTP status** ("200", "404", "400", "403", "timeout", "network"). It is the transport code, **not** a verdict on availability — in particular `djen_raw="200"` does **NOT** mean the caderno exists (see next bullet). Derive `djen_status` from the full response (status + body), and once derived, trust `djen_status` — not a bare reading of `djen_raw`.
- **A `200` can still be genuinely absent.** When there is no publication, DJEN returns HTTP **200 with body `{"status": "Sem comunicações"}`** (no download URL). `get_caderno_url` correctly raises `DJENNotFoundError(status_code=200)` for this. So **availability = HTTP 200 *and* a download URL in the body**; a 200-without-URL is `absent`, exactly like a 404. Do not equate `djen_raw="200"` with `djen_status="available"`.
- Engine runs 3 independent worker pools: **checkers** (DJEN API), **downloaders** (fetch ZIP), **uploaders** (push to IA).
- Periodic IA upload every 10 min protects against crashes.
- Phase 0 uses IA advanced search to discover existing items, then fetches metadata in parallel (~50 concurrent).
- **IA item naming**: Items use `djen-{tribunal}-{year}` format (e.g. `djen-tjro-2025`). The old `djen-YYYY-MM-DD` per-day format is discontinued. ZIP files inside items still use `djen-YYYY-MM-DD-{TRIBUNAL}.zip`.

### Manifest query contracts (web)

The frontend declares its data needs via `.qmd` files in `web/src/queries/`. Each has YAML frontmatter (`output: /data/foo.json`, `format: array|object`) and a SQL block. Backend script `scripts/render_queries.py` executes them against the manifest and writes JSON to `web/public/data/`.

**When frontend needs a new dataset:** add a `.qmd`, add a Zod schema + registry entry in `web/src/lib/data/contracts.ts`, load it com `loadContract('name')` de `web/src/lib/data`, done. Python backend doesn't care.

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

- **Never treat 403 as absent.** CloudFront/WAF returns 403 when rate-limiting. Genuine absent is: **404**, **400** (holidays), **or 200 with body `"Sem comunicações"`** (no download URL). A bare 200 status is *not* enough to call it available.
- **`djen_raw="200"` + `djen_status="available"` is NOT self-consistent proof — historically.** ~79K legacy rows were recorded by an older checker that read only the HTTP 200 and never inspected the body — they were actually "Sem comunicações" (absent). This was fixed by promoting the corrected `sync-manifest.parquet` (built from the probe **upload-delta** corrections) to the sole source of truth (see `docs/planning/manifest-source-of-truth.md` Fase 1); the legacy `sync-manifest.csv` was never backfilled and is no longer read by anything (Fase 3). Before "fixing" any available/absent discrepancy you find elsewhere, **verify against live DJEN** (sample → `get_caderno_url`) — do not assume a recorded status is right just because it looks canonical.
- **Don't trust `absent` from old runs.** If auditing shows false positives, reset all `absent` entries (where `djen_raw` is empty) to unknown.
- **Upload bug:** `ia_s3._perform_upload` must use `file_path.read_bytes()`, not `file_path.open("rb")` as content — sync file objects don't work with `AsyncClient`.
- **Per-item lock + token bucket for IA uploads** (in `src/djen_backup/archive.py`). IA serializes writes per item. `ItemBusyError` → re-queue, don't block.

### Performance

- Rate-limit observer updates (`_notify_counts` throttled to 2Hz) — `manifest.counts()` scans 157K entries; calling it per mark is an event-loop killer.
- Cache `has_uploaded_entries` / `counts` in `SyncManifest`; invalidate on mutation.
- For sampling/debugging absent entries, see patterns in previous audit (sample → `get_caderno_url` live).

### CSS token boundary

There is one design system, not two: **Panda CSS** via the `cobogo` preset (`web/panda.config.ts`). Almost every page styles through `css()`/`styled-system/recipes` (`alert`, `badge`, `card`, `table`, …) reading Panda's own tokens directly — this is the Cobogó/Panda reboot (#1169) and it now covers all substantive pages (the only two holdouts, `advogados.astro` and `comparador.astro`, are trivial redirect stubs to `/stats`).

`web/src/index.css` is a **compatibility bridge**, not a second token system for a page category: it defines `--cg-*` primitives backed by Panda's `--colors-*`/`--fonts-*`, and re-exposes legacy custom-property names (`--papel-*`, `--s-*`, `--color-*`) as aliases to those same values. Those legacy names are consumed only inside the `<style>` blocks of four Svelte islands that predate the reboot and haven't been converted to Panda `css()` yet: `ProcessoLookup.svelte`, `PublicationSearch.svelte`, `SavedConsultations.svelte`, `TribunalCalendar.svelte` (several call sites already fall back to the semantic alias, e.g. `var(--papel-20, var(--color-surface))`). `--pico-*` and `--tinta-*` no longer exist anywhere in the codebase.

- New pages/components: use Panda (`css()`/recipes from the `cobogo` preset). Don't invent bespoke custom properties outside `panda.config.ts`.
- Maintaining one of the four legacy Svelte islands above: it's fine to keep using its existing `--papel-*`/`--s-*` names; don't introduce new ones, and prefer routing through the semantic aliases already declared in `index.css`.
- There is no "marketing vs. data page" split to preserve — don't reintroduce one.

### Style

- Ruff is strict. Only formatter-incompatible ignores + accepted-pattern ignores are in `ruff.toml` (see comments).
- **No blind `except Exception`.** Use specific types: `httpx.HTTPError`, `httpx.RequestError`, `OSError`, `RuntimeError`.
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
