#!/usr/bin/env python3
"""Execute .qmd query files against the manifest and emit JSON.

Purpose:  Turn the frontend's .qmd query contracts into the JSON datasets it loads.
Problem:  The web app declares its data needs as .qmd files; something must execute
          them against the manifest without depending on the Quarto binary.
Strategy: Scan web/src/queries/*.qmd, parse the frontmatter (output/format) + SQL
          fence, run each against the manifest via DuckDB, and write JSON under
          web/public — staying Quarto-compatible for later HTML rendering.
Status:   production — runs in deploy-web.yml (--strict), test.yml (--check) and
          update-catalog.yml; the canonical manifest→frontend data path (see
          web/src/queries/README.md).

Modes (RFC 0007 — fail-loud data contracts):
  (default)   render all contracts; missing optional sources warn, nothing fatal.
  --check     static validation, no network: frontmatter fields + SQL executed
              against synthetic empty schemas derived from the same view registry
              the render uses. Exit 1 listing every invalid .qmd.
  --strict    render; a required (non-``optional``) contract that cannot produce
              its JSON fails the run with exit 1. Used by deploy-web.yml.

Frontmatter contract:
  output: /data/foo.json    # path under web/public (must start with /data/)
  format: array | object    # array of rows OR single row object
  optional: true            # optional contract — data source may be absent

Data sources available in SQL: see VIEW_SPECS below.
"""

from __future__ import annotations

import contextlib

# Safely reconfigure standard output and standard error encoding error handling on Windows
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import argparse
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Callable

import duckdb
import yaml


ROOT = Path(__file__).resolve().parent.parent

# Running as `python scripts/render_queries.py` puts scripts/ (not the repo
# root) on sys.path — add the root so `scripts.reconcile_processos` imports.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from djen_backup.manifest import HEADER as _MANIFEST_HEADER
from scripts.reconcile_processos import (
    _DJEN_AGG_SQL,
    _DOCUMENTOS_SQL,
    _JURIS_AGG_SQL,
    _STJ_AGG_SQL,
    _UNIFICADOS_SQL,
)
from tjro_juris.__main__ import _PARQUET_SCHEMA as _TJRO_JURIS_SCHEMA


QUERIES_DIR = ROOT / "web" / "src" / "queries"
PUBLIC_DIR = ROOT / "web" / "public"
MANIFEST_PARQUET_URL = "https://archive.org/download/causaganha-dashboard/sync-manifest.parquet"
LOCAL_MANIFEST_PARQUET = ROOT / "data" / "sync-manifest.parquet"

# Local dev/CI fallback: exported parquet snapshots from the ratings pipeline.
# Views are only registered when the files exist; contracts that depend on
# them declare `optional: true` and are skipped with a named warning.
DEV_RATINGS_DIR = ROOT / "data" / "parquets"

# Optional parquet views for STJ and TJRO JURIS corpora.
# When the consolidated parquets are present locally (after running the
# respective ingestão pipelines), these views power stj_* and juris_* queries.
_STJ_PARQUET = ROOT / "data" / "stj" / "stj-acordaos.parquet"
_STJ_PARQUET_IA_URL = (
    "https://archive.org/download/stj-acordaos-primeira-secao/stj-acordaos.parquet"
)

_PROCESSOS_UNIFICADOS_PARQUET = ROOT / "data" / "processos_unificados.parquet"
_PROCESSO_DOCUMENTOS_PARQUET = ROOT / "data" / "processo_documentos.parquet"
_PROCESSOS_IA_URL = "https://archive.org/download/causaganha-dashboard/processos_unificados.parquet"
_DOCUMENTOS_IA_URL = "https://archive.org/download/causaganha-dashboard/processo_documentos.parquet"

# DDL that produces the catalog tables exported as lawyer_ratings.parquet /
# ratings_history.parquet (scripts/pipeline/export_ratings.py) — reused as the
# synthetic schema source for --check.
_CATALOG_SCHEMA_SQL = ROOT / "src" / "causaganha" / "storage" / "schema.sql"

SQL_FENCE_RE = re.compile(
    r"```\s*\{\s*sql[^}]*\}\s*\n(.*?)\n```",
    re.DOTALL,
)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

_ALLOWED_FORMATS = ("array", "object")
_OUTPUT_PREFIX = "/data/"


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


def validate_frontmatter(frontmatter: dict[str, Any]) -> list[str]:
    """Return a list of contract violations in the frontmatter (empty = valid)."""
    errors: list[str] = []

    output = frontmatter.get("output")
    if not output:
        errors.append("missing required frontmatter field 'output'")
    elif not str(output).startswith(_OUTPUT_PREFIX):
        errors.append(f"'output' must start with '{_OUTPUT_PREFIX}' (got {output!r})")

    fmt = frontmatter.get("format")
    if not fmt:
        errors.append("missing required frontmatter field 'format'")
    elif fmt not in _ALLOWED_FORMATS:
        errors.append(f"'format' must be one of {list(_ALLOWED_FORMATS)} (got {fmt!r})")

    if not isinstance(frontmatter.get("optional", False), bool):
        errors.append("'optional' must be a boolean")

    return errors


def _try_download_parquet(url: str, dest: Path, label: str) -> Path | None:
    """Download parquet from IA if not present locally; return path or None."""
    if dest.exists():
        print(f"Using local {label}: {dest}")
        return dest
    print(f"Downloading {label} from IA: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            dest.write_bytes(resp.read())
    except OSError as exc:
        print(f"  WARNING: could not download {label} — {exc}", file=sys.stderr)
        return None
    return dest


# ── View registry ──────────────────────────────────────────────────────────────
# Single source of truth for the data sources available to .qmd SQL, in BOTH
# modes: `register` wires the real data for rendering; `synthetic` creates an
# empty relation with the same columns for --check (no network, no files).


@dataclass(frozen=True)
class ViewSpec:
    """A named SQL data source: real registration + synthetic schema for --check."""

    name: str
    register: Callable[[duckdb.DuckDBPyConnection], bool]
    synthetic: Callable[[duckdb.DuckDBPyConnection], None]


def _register_view_from_parquet(con: duckdb.DuckDBPyConnection, name: str, path: Path) -> None:
    con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")


def _register_manifest(con: duckdb.DuckDBPyConnection) -> bool:
    path = _try_download_parquet(MANIFEST_PARQUET_URL, LOCAL_MANIFEST_PARQUET, "manifest")
    if path is None:
        return False
    _register_view_from_parquet(con, "manifest", path)
    return True


def _register_local_parquet(con: duckdb.DuckDBPyConnection, name: str, path: Path) -> bool:
    if not path.exists():
        return False
    print(f"Using local {name}: {path}")
    _register_view_from_parquet(con, name, path)
    return True


def _register_lawyer_ratings(con: duckdb.DuckDBPyConnection) -> bool:
    return _register_local_parquet(
        con, "lawyer_ratings", DEV_RATINGS_DIR / "lawyer_ratings.parquet"
    )


def _register_ratings_history(con: duckdb.DuckDBPyConnection) -> bool:
    return _register_local_parquet(
        con, "ratings_history", DEV_RATINGS_DIR / "ratings_history.parquet"
    )


def _register_acordaos(con: duckdb.DuckDBPyConnection) -> bool:
    stj_parquet = _try_download_parquet(_STJ_PARQUET_IA_URL, _STJ_PARQUET, "STJ parquet")
    if stj_parquet is None:
        return False
    # qmd files query "FROM acordaos" — register under that name
    _register_view_from_parquet(con, "acordaos", stj_parquet)
    return True


def _register_processos_unificados(con: duckdb.DuckDBPyConnection) -> bool:
    path = _try_download_parquet(
        _PROCESSOS_IA_URL, _PROCESSOS_UNIFICADOS_PARQUET, "processos_unificados"
    )
    if path is None:
        return False
    _register_view_from_parquet(con, "processos_unificados", path)
    return True


def _register_processo_documentos(con: duckdb.DuckDBPyConnection) -> bool:
    path = _try_download_parquet(
        _DOCUMENTOS_IA_URL, _PROCESSO_DOCUMENTOS_PARQUET, "processo_documentos"
    )
    if path is None:
        return False
    _register_view_from_parquet(con, "processo_documentos", path)
    return True


def _register_tjro_juris(con: duckdb.DuckDBPyConnection) -> bool:
    # Consolidate command writes: data/tjro_juris/<year>/tjro-juris-<year>.parquet
    juris_files = sorted(ROOT.glob("data/tjro_juris/*/tjro-juris-*.parquet"))
    if not juris_files:
        return False
    juris_list = ", ".join(f"'{p}'" for p in juris_files)
    print(f"Using local JURIS parquets: {len(juris_files)} files")
    con.execute(f"CREATE VIEW tjro_juris AS SELECT * FROM read_parquet([{juris_list}])")
    return True


# ── Synthetic schemas (for --check) ────────────────────────────────────────────


def _synthetic_manifest(con: duckdb.DuckDBPyConnection) -> None:
    """Empty manifest with columns from djen_backup.manifest.HEADER (the CSV writer).

    Types mirror what read_csv_auto infers on the real CSV.
    """
    type_overrides = {"date": "DATE", "updated_at": "TIMESTAMP"}
    cols = ", ".join(
        f"{col} {type_overrides.get(col, 'VARCHAR')}" for col in _MANIFEST_HEADER.split(",")
    )
    con.execute(f"CREATE TABLE manifest ({cols})")


def _synthetic_catalog_table(con: duckdb.DuckDBPyConnection, table: str) -> None:
    """Empty `table` with the schema from storage/schema.sql.

    That DDL defines the catalog tables that export_ratings.py copies verbatim
    to the parquets consumed here — same definition, not a hand copy.
    """
    scratch = duckdb.connect()
    try:
        scratch.execute(_CATALOG_SCHEMA_SQL.read_text(encoding="utf-8"))
        empty = scratch.execute(f"SELECT * FROM {table} LIMIT 0").arrow()
    finally:
        scratch.close()
    con.register(table, empty)


def _synthetic_lawyer_ratings(con: duckdb.DuckDBPyConnection) -> None:
    _synthetic_catalog_table(con, "lawyer_ratings")


def _synthetic_ratings_history(con: duckdb.DuckDBPyConnection) -> None:
    _synthetic_catalog_table(con, "ratings_history")


# The STJ parquet schema is auto-detected from the portal's JSON by
# stj_acordaos.dedup (no static schema exists in-repo), so this is the single
# in-repo definition of the columns the .qmd contracts and reconcile SQL use.
_ACORDAOS_SYNTHETIC_COLUMNS: dict[str, str] = {
    "id": "VARCHAR",
    "numeroProcesso": "VARCHAR",
    "siglaClasse": "VARCHAR",
    "ministroRelator": "VARCHAR",
    "tema": "VARCHAR",
    "teseJuridica": "VARCHAR",
    "ementa": "VARCHAR",
    "dataDecisao": "DATE",
    "dataPublicacao": "DATE",
}


def _synthetic_acordaos(con: duckdb.DuckDBPyConnection) -> None:
    cols = ", ".join(f'"{col}" {typ}' for col, typ in _ACORDAOS_SYNTHETIC_COLUMNS.items())
    con.execute(f"CREATE TABLE acordaos ({cols})")


def _synthetic_tjro_juris(con: duckdb.DuckDBPyConnection) -> None:
    """Empty tjro_juris from the producer's own parquet schema (tjro_juris CLI)."""
    con.register("tjro_juris", _TJRO_JURIS_SCHEMA.empty_table())


def _reconcile_sources_connection() -> duckdb.DuckDBPyConnection:
    """Scratch connection with empty inputs + aggregation views of reconcile_processos.

    The processos_unificados/processo_documentos schemas are derived by running
    the producer's own SQL (scripts/reconcile_processos.py) over empty sources,
    so --check can never drift from what the reconcile pipeline actually writes.
    """
    scratch = duckdb.connect()
    # The reconcile pipeline reads a publication-level manifest (one row per
    # numero_processo/publication) — distinct from the sync-manifest CSV view.
    scratch.execute(
        "CREATE TABLE manifest (numero_processo VARCHAR, data_publicacao DATE, tribunal VARCHAR)"
    )
    _synthetic_tjro_juris(scratch)
    _synthetic_acordaos(scratch)
    scratch.execute(f"CREATE VIEW djen_agg AS {_DJEN_AGG_SQL}")
    scratch.execute(f"CREATE VIEW juris_agg AS {_JURIS_AGG_SQL}")
    scratch.execute(f"CREATE VIEW stj_agg AS {_STJ_AGG_SQL}")
    return scratch


def _synthetic_from_reconcile_sql(con: duckdb.DuckDBPyConnection, name: str, sql: str) -> None:
    scratch = _reconcile_sources_connection()
    try:
        empty = scratch.execute(f"SELECT * FROM ({sql}) LIMIT 0").arrow()
    finally:
        scratch.close()
    con.register(name, empty)


def _synthetic_processos_unificados(con: duckdb.DuckDBPyConnection) -> None:
    _synthetic_from_reconcile_sql(con, "processos_unificados", _UNIFICADOS_SQL)


def _synthetic_processo_documentos(con: duckdb.DuckDBPyConnection) -> None:
    _synthetic_from_reconcile_sql(con, "processo_documentos", _DOCUMENTOS_SQL)


VIEW_SPECS: tuple[ViewSpec, ...] = (
    ViewSpec("manifest", _register_manifest, _synthetic_manifest),
    ViewSpec("lawyer_ratings", _register_lawyer_ratings, _synthetic_lawyer_ratings),
    ViewSpec("ratings_history", _register_ratings_history, _synthetic_ratings_history),
    ViewSpec("acordaos", _register_acordaos, _synthetic_acordaos),
    ViewSpec(
        "processos_unificados", _register_processos_unificados, _synthetic_processos_unificados
    ),
    ViewSpec("processo_documentos", _register_processo_documentos, _synthetic_processo_documentos),
    ViewSpec("tjro_juris", _register_tjro_juris, _synthetic_tjro_juris),
)


# ── Execution ──────────────────────────────────────────────────────────────────


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


def _first_line(exc: duckdb.Error) -> str:
    return str(exc).splitlines()[0] if str(exc) else type(exc).__name__


def check_queries(queries_dir: Path | None = None) -> list[str]:
    """Statically validate all .qmd contracts (frontmatter + SQL). No network.

    SQL is executed against empty synthetic relations built from the same
    VIEW_SPECS registry the render uses, catching syntax errors, unknown
    columns and references to unregistered views. Returns the list of
    failures (empty = all contracts valid).
    """
    queries_dir = QUERIES_DIR if queries_dir is None else queries_dir
    qmds = sorted(queries_dir.glob("*.qmd"))
    if not qmds:
        return [f"no .qmd files found in {queries_dir}"]

    con = duckdb.connect()
    for spec in VIEW_SPECS:
        spec.synthetic(con)

    failures: list[str] = []
    for qmd in qmds:
        errors: list[str] = []
        try:
            frontmatter, sql = parse_qmd(qmd)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            errors.extend(validate_frontmatter(frontmatter))
            try:
                con.execute(sql)
            except duckdb.Error as exc:
                errors.append(f"SQL error: {_first_line(exc)}")

        if errors:
            print(f"FAIL {qmd.name}")
            for error in errors:
                print(f"     - {error}")
            failures.extend(f"{qmd.name}: {error}" for error in errors)
        else:
            print(f"OK   {qmd.name}")

    return failures


def render_all(
    queries_dir: Path | None = None,
    public_dir: Path | None = None,
    specs: tuple[ViewSpec, ...] | None = None,
) -> tuple[int, list[str]]:
    """Render all .qmd files. Returns (rendered_count, failures).

    A failure is a contract that should have produced JSON but could not:
    invalid frontmatter, or a missing data source for a non-``optional``
    contract. Optional contracts with missing sources emit a named warning
    and are not failures. The caller decides whether failures are fatal
    (--strict) or merely reported.
    """
    queries_dir = QUERIES_DIR if queries_dir is None else queries_dir
    public_dir = PUBLIC_DIR if public_dir is None else public_dir
    specs = VIEW_SPECS if specs is None else specs
    qmds = sorted(queries_dir.glob("*.qmd"))
    if not qmds:
        print(f"No .qmd files in {queries_dir}", file=sys.stderr)
        return 0, []

    con = duckdb.connect()
    for spec in specs:
        spec.register(con)

    count = 0
    failures: list[str] = []
    for qmd in qmds:
        print(f"\n→ {qmd.name}")
        try:
            frontmatter, sql = parse_qmd(qmd)
        except ValueError as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            failures.append(f"{qmd.name}: {exc}")
            continue

        fm_errors = validate_frontmatter(frontmatter)
        if fm_errors:
            print(f"  ERROR: invalid frontmatter — {'; '.join(fm_errors)}", file=sys.stderr)
            failures.append(f"{qmd.name}: {'; '.join(fm_errors)}")
            continue

        output = frontmatter["output"]
        fmt = frontmatter["format"]
        optional = frontmatter.get("optional", False)

        try:
            data = run_query(con, sql, fmt)
        except duckdb.CatalogException as exc:
            reason = _first_line(exc)
            if optional:
                print(
                    f"  WARNING: optional contract skipped — {reason}; {output} not generated",
                    file=sys.stderr,
                )
            else:
                print(f"  ERROR: required contract failed — {reason}", file=sys.stderr)
                failures.append(f"{qmd.name}: missing required data source — {reason}")
            continue

        output_path = public_dir / output.lstrip("/")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, indent=2, default=json_default),
            encoding="utf-8",
        )
        print(f"  → {output_path} ({output_path.stat().st_size:,} bytes)")
        count += 1

    return count, failures


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(description="Render .qmd query contracts to JSON.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate frontmatter and SQL against synthetic schemas (no network, "
        "no files written); exit 1 listing every invalid .qmd",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if any required (non-optional) contract fails to render",
    )
    args = parser.parse_args(argv)

    if args.check:
        failures = check_queries()
        if failures:
            print(f"\n--check failed: {len(failures)} problem(s):", file=sys.stderr)
            for failure in failures:
                print(f"  - {failure}", file=sys.stderr)
            return 1
        print("\n--check passed: all query contracts are valid.")
        return 0

    count, failures = render_all()
    print(f"\n{count} queries rendered.")
    if failures:
        print(f"{len(failures)} contract(s) failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
