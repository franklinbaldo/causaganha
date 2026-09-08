"""One shared, tested source of truth for the absent self-consistency rule.

``SyncManifest._normalize_event`` (in-memory engine) and
``render_manifest_parquet._normalize_manifest`` (DuckDB-SQL batch compactor)
already independently drifted once (PR #1323, downgrading absent+empty-raw
rows to unknown). This test pins both to ``djen_backup.absent_consistency``
so a future change to the rule cannot silently update only one runtime.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import duckdb
import pytest

from djen_backup.absent_consistency import (
    NO_PUBLICATIONS_SENTINEL,
    normalize_absent,
)
from djen_backup.manifest import SyncManifest


def _load_render_module():
    spec = importlib.util.spec_from_file_location(
        "render_manifest_parquet",
        Path(__file__).resolve().parents[1] / "scripts" / "render_manifest_parquet.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── SyncManifest delegates to the shared rule ───────────────────────


def test_normalize_event_delegates_to_shared_rule() -> None:
    """``_normalize_event`` still does its own confirmed->available rewrite

    (engine-only vocabulary, not part of the absent self-consistency rule),
    but the absent handling itself must be the shared function, not a
    re-typed copy of its logic.
    """
    source = inspect.getsource(SyncManifest._normalize_event)
    assert "normalize_absent" in source


# ── the DuckDB compactor's SQL literals come from the shared constants ──


def test_normalize_manifest_sql_uses_shared_sentinel() -> None:
    rmp = _load_render_module()
    assert rmp.ABSENT_SELF_CONSISTENCY_SENTINEL is NO_PUBLICATIONS_SENTINEL


# ── fixture-driven cross-consistency: SQL path vs. Python path ─────


ABSENT_FIXTURE_ROWS: list[tuple[str, str]] = [
    ("absent", "200"),
    ("absent", "200: some body"),
    ("absent", "404"),
    ("absent", ""),
    ("available", "200"),
    ("confirmed", "200"),
]


@pytest.mark.parametrize(("djen_status", "djen_raw"), ABSENT_FIXTURE_ROWS)
def test_sql_normalization_agrees_with_python_rule(djen_status: str, djen_raw: str) -> None:
    rmp = _load_render_module()
    con = duckdb.connect()
    con.execute("CREATE TABLE manifest (tribunal VARCHAR, djen_status VARCHAR, djen_raw VARCHAR)")
    con.execute(
        "INSERT INTO manifest VALUES ('TJRO', ?, ?)",
        [djen_status, djen_raw],
    )

    rmp._normalize_manifest(con)  # noqa: SLF001

    sql_status, sql_raw = con.execute("SELECT djen_status, djen_raw FROM manifest").fetchone()

    py_status, py_raw = normalize_absent(djen_status, djen_raw)

    # Compare the real stored values, not a coerced approximation: a SQL NULL
    # and Python's "" both mean "unknown", but they are not the same value
    # and downstream .qmd queries only ever test for `djen_status = ''`
    # (see totals.qmd/tribunal_coverage.qmd) -- a NULL silently disagrees.
    assert (sql_status, sql_raw) == (py_status, py_raw)
