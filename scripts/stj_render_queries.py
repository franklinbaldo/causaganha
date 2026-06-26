#!/usr/bin/env python3
"""Execute STJ .qmd query files against the acórdãos parquet and emit JSON.

Same pattern as scripts/render_queries.py but for STJ-specific queries
(web/src/queries/stj_*.qmd).

Frontmatter contract:
  output: /data/stj_foo.json   # path under web/public
  format: array | object       # array of rows OR single row object

Data sources available in SQL:
  acordaos    -- view over the STJ acórdãos parquet file
"""

from __future__ import annotations

import contextlib
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import json
import re
from pathlib import Path
from typing import Any

import duckdb
import yaml


QUERIES_DIR = Path(__file__).parent.parent / "web" / "src" / "queries"
PUBLIC_DIR = Path(__file__).parent.parent / "web" / "public"
DEFAULT_PARQUET = Path(__file__).parent.parent / "data" / "stj" / "stj-acordaos.parquet"

SQL_FENCE_RE = re.compile(
    r"```\s*\{\s*sql[^}]*\}\s*\n(.*?)\n```",
    re.DOTALL,
)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_qmd(path: Path) -> tuple[dict[str, Any], str]:
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


def run_query(con: duckdb.DuckDBPyConnection, sql: str, fmt: str) -> object:
    rows = con.execute(sql).fetchall()
    columns = [d[0] for d in con.description]

    if fmt == "object":
        if len(rows) != 1:
            msg = f"format=object expects 1 row, got {len(rows)}"
            raise ValueError(msg)
        return dict(zip(columns, rows[0], strict=False))

    return [dict(zip(columns, row, strict=False)) for row in rows]


def json_default(obj: object) -> str:
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def render_all(parquet_path: Path | None = None) -> int:
    qmds = sorted(QUERIES_DIR.glob("stj_*.qmd"))
    if not qmds:
        print(f"No stj_*.qmd files in {QUERIES_DIR}", file=sys.stderr)
        return 0

    pq = parquet_path or DEFAULT_PARQUET
    if not pq.exists():
        print(f"ERROR: Parquet not found at {pq}", file=sys.stderr)
        print("Run `stj-acordaos download && stj-acordaos upload` first.", file=sys.stderr)
        return 0

    print(f"Using parquet: {pq}")
    con = duckdb.connect()
    con.execute(f"CREATE VIEW acordaos AS SELECT * FROM read_parquet('{pq}')")

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
    import argparse

    parser = argparse.ArgumentParser(description="Render STJ .qmd queries to JSON.")
    parser.add_argument("--parquet", type=Path, default=None, help="Path to STJ parquet file.")
    args = parser.parse_args()

    n = render_all(parquet_path=args.parquet)
    print(f"\n{n} queries rendered.")
