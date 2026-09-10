"""Behavior tests for scripts/ia_practicality_probe.py's probe_parquet().

probe_parquet() reads a Parquet file via DuckDB's httpfs extension, using
a URL built from IA_DOWNLOAD_BASE + item_id + filename. These tests point
IA_DOWNLOAD_BASE at a local temp directory so DuckDB reads the fixture
Parquet file directly, without touching the network.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from scripts import ia_practicality_probe as mod


def _write_parquet(path: Path, rows: list[tuple]) -> None:
    con = duckdb.connect()
    try:
        con.execute("CREATE TABLE t (id INTEGER, tribunal VARCHAR, data_disponibilizacao VARCHAR)")
        con.executemany("INSERT INTO t VALUES (?, ?, ?)", rows)
        con.execute(f"COPY t TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()


@pytest.fixture
def local_ia_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(mod, "IA_DOWNLOAD_BASE", str(tmp_path))
    return tmp_path


def test_probe_parquet_result_has_no_dead_warnings_field(local_ia_base: Path) -> None:
    """probe_parquet()'s result dict must not promise an unpopulated 'warnings' key."""
    item_dir = local_ia_base / "djen-tjro-2026"
    item_dir.mkdir()
    _write_parquet(item_dir / "comunicacoes.parquet", [(1, "TJRO", "2026-01-01")])

    result = mod.probe_parquet("djen-tjro-2026", "comunicacoes.parquet")

    assert "warnings" not in result
    assert result["status"] == "ok"
    assert result["rows"] == 1


def test_probe_parquet_flags_missing_required_columns(local_ia_base: Path) -> None:
    item_dir = local_ia_base / "djen-tjro-2026"
    item_dir.mkdir()
    con = duckdb.connect()
    try:
        con.execute("CREATE TABLE t (id INTEGER)")
        con.execute("INSERT INTO t VALUES (1)")
        con.execute(f"COPY t TO '{item_dir / 'comunicacoes.parquet'}' (FORMAT PARQUET)")
    finally:
        con.close()

    result = mod.probe_parquet("djen-tjro-2026", "comunicacoes.parquet")

    assert result["status"] == "fail"
    assert any("missing required columns" in e for e in result["errors"])
