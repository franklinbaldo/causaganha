# Query Contract

The frontend declares its data needs via `.qmd` files in this directory. The
backend executes them and publishes JSON to `web/public/`, which the frontend
then fetches.

## Syntax

Each `.qmd` file uses [Quarto](https://quarto.org/) markdown with:

- **YAML frontmatter** declaring where the result goes
- **Markdown prose** (free-form documentation)
- **SQL code block** (```` ```{sql} ````) that runs against the manifest

## Frontmatter Contract

```yaml
---
title: "Human-readable title"
description: "What this query does."
output: /data/my_query.json    # required; path under web/public/, must start with /data/
format: array | object         # required; array of rows or single-row object
optional: true                 # optional flag (default false) — see below
---
```

### `optional: true`

Contracts whose data source is a parquet that may legitimately not exist yet
(ratings, STJ, JURIS, reconciliation exports) declare `optional: true`. When
the source is missing, the render logs a **named warning** and skips the
contract — it never fails the build. Contracts without the flag are
**required**: under `--strict` a missing source fails the run.

Currently optional: `lawyer_leaderboard`, `stj_totals`, `stj_temas`,
`stj_relatores`, `juris_totals`, `juris_classes`, `juris_orgaos`,
`processos_multi_fonte`.

## Data Sources

The SQL runs against the views registered by `scripts/render_queries.py`
(see `VIEW_SPECS` there — the single registry used by both render and
`--check`):

| View                 | Source                                              |
|----------------------|-----------------------------------------------------|
| manifest             | sync-manifest.parquet (tribunal, date, ia_status, djen_status, djen_raw, updated_at) |
| lawyer_ratings       | data/parquets/lawyer_ratings.parquet (ratings pipeline) |
| ratings_history      | data/parquets/ratings_history.parquet               |
| acordaos             | STJ acórdãos parquet (local or IA download)         |
| processos_unificados | reconcile_processos.py output (local or IA)         |
| processo_documentos  | reconcile_processos.py output (local or IA)         |
| tjro_juris           | data/tjro_juris/\*/tjro-juris-\*.parquet            |

## Example

```qmd
---
title: "Totals"
output: /data/totals.json
format: object
---

Some explanatory markdown here.

```{sql}
SELECT COUNT(*) AS total FROM manifest;
```
```

## Rendering & Validation

Render locally (downloads the manifest if needed):

```sh
uv run python scripts/render_queries.py
```

Validate contracts statically — no network, no files written. Checks the
required frontmatter fields and executes each SQL block against synthetic
empty schemas derived from the same view registry the render uses (catches
syntax errors, unknown columns, unregistered views). Exits non-zero listing
every invalid `.qmd`:

```sh
uv run python scripts/render_queries.py --check
```

Strict render — any **required** (non-`optional`) contract that cannot
produce its JSON fails the run with exit 1; missing optional sources emit a
named warning:

```sh
uv run python scripts/render_queries.py --strict
```

In CI: `test.yml` runs `--check` on every PR; `deploy-web.yml` renders with
`--strict` (RFC 0007 — fail-loud data contracts).

The same `.qmd` files can be rendered by the real Quarto binary later
(for HTML reports) without any changes — the syntax is compatible.
