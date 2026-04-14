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
output: /data/my_query.json    # path under web/public/
format: array | object         # array of rows (default) or single-row object
---
```

## Data Sources

The SQL runs against these views:

| View     | Columns                                                |
|----------|--------------------------------------------------------|
| manifest | tribunal, date, ia_status, djen_status, djen_raw, updated_at |

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

## Rendering

Locally:
```sh
uv run python scripts/render_queries.py
```

In CI: happens automatically during `deploy-web.yml`.

The same `.qmd` files can be rendered by the real Quarto binary later
(for HTML reports) without any changes — the syntax is compatible.
