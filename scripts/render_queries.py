#!/usr/bin/env python3
"""Execute .qmd query files against the manifest and emit JSON.

Scans web/src/queries/*.qmd, parses Quarto-compatible frontmatter
(``output`` and ``format`` fields), extracts the SQL code block,
runs it against the manifest via DuckDB, and writes the result JSON
to web/public{output}.

This is a lightweight replacement for ``quarto render`` — it honors
the same .qmd syntax (frontmatter + ``` {sql} ``` fences) but has no
dependency on the Quarto binary. The same files can be rendered by
Quarto later (for HTML docs, Content Collections, etc.) without
changes.

Frontmatter contract:
  output: /data/foo.json    # path under web/public
  format: array | object    # array of rows OR single row object

Data sources available in SQL:
  manifest                  # view over the sync-manifest CSV
"""

from __future__ import annotations

import contextlib

# Safely reconfigure standard output and standard error encoding error handling on Windows
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

import duckdb
import yaml


QUERIES_DIR = Path(__file__).parent.parent / "web" / "src" / "queries"
PUBLIC_DIR = Path(__file__).parent.parent / "web" / "public"
MANIFEST_CSV_URL = "https://archive.org/download/causaganha-dashboard/sync-manifest.csv"
LOCAL_MANIFEST = Path(__file__).parent.parent / "data" / "sync-manifest.csv"

# Local dev/CI fallback: exported parquet snapshots from the ratings pipeline.
# Views are only registered when the files exist, so production runs that
# lack them will skip gracefully (those queries will fail with a missing-view error).
DEV_RATINGS_DIR = Path(__file__).parent.parent / "data" / "parquets"

SQL_FENCE_RE = re.compile(
    r"```\s*\{\s*sql[^}]*\}\s*\n(.*?)\n```",
    re.DOTALL,
)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_qmd(path: Path) -> tuple[dict[str, Any], str]:
    """Extract frontmatter dict and first SQL block from a .qmd file."""
    text = path.read_text(encoding="utf-8")

    fm_match = FRONTMATTER_RE.match(text)
    if not fm_match:
        msg = f"{path}: missing YAML frontmatter"
        raise ValueError(msg)
    frontmatter = yaml.safe_load(fm_match.group(1)) or {}

    sql_match = SQL_FENCE_RE.search(text)
    if not sql_match:
        msg = f"{path}: no ```{{sql}}``` code block"
        raise ValueError(msg)
    sql = sql_match.group(1).strip()

    return frontmatter, sql


def ensure_manifest() -> Path:
    """Ensure a manifest CSV is available locally."""
    if LOCAL_MANIFEST.exists():
        print(f"Using local manifest: {LOCAL_MANIFEST}")
        return LOCAL_MANIFEST

    print(f"Downloading manifest from {MANIFEST_CSV_URL}...")
    LOCAL_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(MANIFEST_CSV_URL, timeout=120) as resp:
        LOCAL_MANIFEST.write_bytes(resp.read())
    print(f"  saved to {LOCAL_MANIFEST} ({LOCAL_MANIFEST.stat().st_size:,} bytes)")
    return LOCAL_MANIFEST


def run_query(con: duckdb.DuckDBPyConnection, sql: str, fmt: str) -> object:
    """Execute SQL and return serializable data in the requested format."""
    rows = con.execute(sql).fetchall()
    columns = [d[0] for d in con.description]

    if fmt == "object":
        if len(rows) != 1:
            msg = f"format=object expects 1 row, got {len(rows)}"
            raise ValueError(msg)
        return dict(zip(columns, rows[0], strict=False))

    # default: array of row dicts
    return [dict(zip(columns, row, strict=False)) for row in rows]


def json_default(obj: object) -> str:
    """Serialize non-JSON types (date, datetime) as ISO strings."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def render_all() -> int:
    """Render all .qmd files. Returns number rendered."""
    qmds = sorted(QUERIES_DIR.glob("*.qmd"))
    if not qmds:
        print(f"No .qmd files in {QUERIES_DIR}", file=sys.stderr)
        return 0

    manifest_path = ensure_manifest()
    con = duckdb.connect()
    con.execute(
        f"CREATE VIEW manifest AS SELECT * FROM read_csv_auto('{manifest_path}', header=true)"
    )

    ratings_path = DEV_RATINGS_DIR / "lawyer_ratings.parquet"
    if ratings_path.exists():
        print(f"Using local lawyer_ratings: {ratings_path}")
        con.execute(
            f"CREATE VIEW lawyer_ratings AS SELECT * FROM read_parquet('{ratings_path}')"
        )

    ratings_history_path = DEV_RATINGS_DIR / "ratings_history.parquet"
    if ratings_history_path.exists():
        print(f"Using local ratings_history: {ratings_history_path}")
        con.execute(
            f"CREATE VIEW ratings_history AS SELECT * FROM read_parquet('{ratings_history_path}')"
        )

    count = 0
    for qmd in qmds:
        print(f"\n→ {qmd.name}")
        frontmatter, sql = parse_qmd(qmd)

        output = frontmatter.get("output")
        if not output:
            print("  SKIP: no 'output' in frontmatter", file=sys.stderr)
            continue
        fmt = frontmatter.get("format", "array")

        output_path = PUBLIC_DIR / output.lstrip("/")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            data = run_query(con, sql, fmt)
        except duckdb.CatalogException as exc:
            print(f"  SKIP: missing table/view — {exc}", file=sys.stderr)
            continue
        output_path.write_text(
            json.dumps(data, indent=2, default=json_default),
            encoding="utf-8",
        )
        print(
            f"  → {output_path.relative_to(PUBLIC_DIR.parent.parent)}"
            f" ({output_path.stat().st_size:,} bytes)"
        )
        count += 1

    return count


if __name__ == "__main__":
    n = render_all()
    print(f"\n{n} queries rendered.")
