"""Shared fixtures for consolidate BDD tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import duckdb


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def manifest_path(tmp_path: Path) -> Path:
    """Path to a disposable canonical manifest parquet per test."""
    return tmp_path / "sync-manifest.parquet"


def write_manifest(path: Path, rows: list[dict]) -> None:
    """Write a canonical manifest parquet with the expected schema."""
    con = duckdb.connect()
    try:
        con.execute("CREATE TABLE manifest (tribunal VARCHAR, date DATE, ia_status VARCHAR, djen_status VARCHAR, djen_raw VARCHAR, updated_at VARCHAR)")
        values = [(row.get("tribunal", "TJSP"), row["date"], row.get("ia_status", ""), row.get("djen_status", ""), row.get("djen_raw", ""), row.get("updated_at", "")) for row in rows]
        if values:
            con.executemany("INSERT INTO manifest VALUES (?, ?, ?, ?, ?, ?)", values)
        con.execute("COPY manifest TO ? (FORMAT PARQUET)", [str(path)])
    finally:
        con.close()
