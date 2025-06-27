Below is a **fully-fleshed “Plan B”** that replaces Alembic + hand-rolled runners with **dbt-duckdb** as the single engine for DDL, tests, and documentation.
I keep it opinionated, minimal, and focused on what you need for *causa\_ganha* right now; bolt-ons (snapshots, exposures, Airbyte, etc.) can be added later.

---

## 0 — Why dbt-duckdb instead of Alembic

* **One binary (`dbt`) rules them all**: DDL, tests, lineage docs, CI drift-checks.
* **No dialect hacks**: the adapter is maintained by DuckDB core devs and supports full SQL + Parquet/CSV external tables. ([github.com][1])
* **Reversible in dev, idempotent in prod**: models are re-built from source on every `dbt build`; you only keep data you care about.
* **Built-in data quality**: null-checks and uniqueness tests live next to the model code. ([docs.getdbt.com][2])

If tomorrow you outgrow the embedded file, switch the profile to MotherDuck or Postgres and keep the same models.

---

## 1 — Install & bootstrap

```bash
# 1. Add dbt + adapter to your Python env
uv pip install --quiet "dbt-duckdb~=1.9"

# 2. Create project skeleton
dbt init causa_ganha --adapter duckdb
cd causa_ganha
```

*dbt* creates a `profiles.yml` stub in `~/.dbt`. Edit it:

```yaml
causa_ganha:
  target: local
  outputs:
    local:
      type: duckdb
      path: data/causaganha.duckdb          # relative to repo root
```

Now `dbt debug` should succeed and create the file if it doesn’t exist.

---

## 2 — Repo layout (proposed)

```
.
├── data/                       # .duckdb lives here, ignored by Git
├── dbt/                        # dbt project root (renamed for clarity)
│   ├── models/
│   │   ├── staging/            # 1-to-1 raw ingests
│   │   ├── marts/              # final analytical tables (ranking, etc.)
│   │   └── seeds/              # CSV reference data
│   └── tests/                  # generic & singular tests
├── src/                        # your FastAPI + CLI code
└── .github/workflows/          # CI pipeline
```

Add **`data/*.duckdb` to `.gitignore`**.

---

## 3 — Define the base schema

Instead of “migrations”, you author **models**:

`dbt/models/staging/tjro_diary.sql`

```sql
{{ config(materialized='table') }}

CREATE OR REPLACE TABLE {{ this }} AS
SELECT
    dj.id,
    dj.date,
    dj.url_archive,
    dj.file_hash
FROM read_parquet('raw/tjro_diary_*.parquet') dj;
```

`dbt/models/marts/advocate_ranking.sql`

```sql
{{ config(materialized='table') }}

WITH extracted AS (
    SELECT
        partes->>'advocate'        AS advocate,
        partes->>'outcome'         AS outcome
    FROM {{ ref('tjro_diary') }}
)
SELECT
    advocate,
    elo_ranking(outcome) AS elo
FROM extracted
GROUP BY 1;
```

Add **tests** right next to them:

`dbt/models/marts/advocate_ranking.yml`

```yaml
version: 2
models:
  - name: advocate_ranking
    columns:
      - name: advocate
        tests: [not_null, unique]
```

dbt will refuse to finish a build if those constraints fail.

---

## 4 — Running locally

```bash
# one-off full build
dbt build                 # run + test + docs
# iterative dev
dbt run --select staging.tjro_diary
dbt test --select advocate_ranking
# drop everything & rebuild (alpha phase)
rm data/causaganha.duckdb
dbt build
```

Because DuckDB is embedded, this is instant (< 2 s on typical dev boxes).
Need “migrations” for destructive changes? Just change the model SQL and rerun; old objects are replaced.

---

## 5 — Integrate with your CLI

Add a thin wrapper so the old command still works:

```python
def db_migrate():
    """Rebuild dbt models to latest state."""
    subprocess.check_call(["dbt", "build", "--project-dir", "dbt"])
```

`uv run causaganha db migrate` now calls dbt under the hood—no code changes elsewhere.

---

## 6 — CI pipeline (GitHub Actions)

```yaml
name: CausaGanha DBT

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: |
          pip install --quiet "dbt-duckdb~=1.9"
      - name: Build & test
        run: dbt build --project-dir dbt
      - name: Drift check
        run: >
          dbt run-operation list_unbuilt_models --args '{"compiled": false}' |
          grep '.' && { echo "Schema drift detected"; exit 1; } || true
```

The **drift check** makes the build fail if any model isn’t materialised—equivalent to “pending migration”.

---

## 7 — Seeds, snapshots & docs (optional but powerful)

| Feature       | Why you might care                                   | How to enable                          |
| ------------- | ---------------------------------------------------- | -------------------------------------- |
| **Seeds**     | Keep small lookup CSVs (court codes, state abbrevs). | Place CSV in `seeds/` → `dbt seed`.    |
| **Snapshots** | Track slowly-changing advocate status.               | `dbt snapshot` with `unique_key`.      |
| **Docs**      | Auto-generate lineage site.                          | `dbt docs generate && dbt docs serve`. |

---

## 8 — Handling irreversible DDL (DROP COLUMN)

DuckDB still lacks easy `ALTER TABLE DROP COLUMN`. When that day comes:

```bash
# create a patch script
dbt run-operation drop_column --args '{"table": "tjro_diary", "column": "foo"}'
```

Store the macro in `macros/ops/drop_column.sql` so it is version-controlled and replayable.

---

## 9 — Local reset script (alpha only)

```bash
#!/usr/bin/env bash
set -e
rm -f data/causaganha.duckdb
dbt build --project-dir dbt
echo "✅ Fresh DB built"
```

Wire it to your CLI as `causaganha db reset`.

---

## 10 — Pull-request checklist (dbt edition)

* [ ] All changed/added models pass `dbt build`.
* [ ] Added/updated tests cover new columns.
* [ ] `dbt docs generate` shows no duplicate or disabled objects.
* [ ] CI drift check green.

---

### Upshot

*You trade thousands of lines of Alembic boilerplate for \~200 lines of model SQL and a rock-solid testing layer.*
dbt-duckdb keeps everything reproducible, reviewable, and future-proof—with virtually zero friction on laptops.

If at some point you need more traditional, file-based migrations (e.g., packaged releases for on-prem clients), bolt **Dbmate** on top for just those DDL patches and keep using dbt for everything analytic. Until then, dbt alone will carry you comfortably to production.

[1]: https://github.com/duckdb/dbt-duckdb?utm_source=chatgpt.com "dbt (http://getdbt.com) adapter for DuckDB (http://duckdb.org) - GitHub"
[2]: https://docs.getdbt.com/docs/core/connect-data-platform/duckdb-setup?utm_source=chatgpt.com "DuckDB setup | dbt Developer Hub - dbt Docs"
