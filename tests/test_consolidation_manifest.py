"""Tests for Phase 0.6 consolidation manifest."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from causaganha.consolidate.consolidation_manifest import (
    ManifestItem,
    TableStats,
    collect_table_stats,
    update_consolidation_manifest,
)
from causaganha.consolidate.schema_registry import CURRENT_VERSION, kv_metadata_sql_fragment


@pytest.fixture
def parquet_dir(tmp_path: Path) -> Path:
    fragment = kv_metadata_sql_fragment("djen-2026-06-01")
    con = duckdb.connect()
    con.execute("CREATE TABLE comunicacoes AS SELECT 'uuid-1' AS id, 'TJRO' AS tribunal")
    con.execute(
        f"COPY comunicacoes TO '{tmp_path / 'comunicacoes.parquet'}' "
        f"(FORMAT PARQUET, COMPRESSION ZSTD, {fragment})"
    )
    con.close()
    return tmp_path


class TestCollectTableStats:
    def test_collects_rows_size_sha256(self, parquet_dir: Path) -> None:
        stats = collect_table_stats(parquet_dir, ["comunicacoes"])
        assert "comunicacoes" in stats
        s = stats["comunicacoes"]
        assert s.rows == 1
        assert s.size_bytes > 0
        assert len(s.sha256) == 64

    def test_skips_missing_tables(self, parquet_dir: Path) -> None:
        stats = collect_table_stats(parquet_dir, ["comunicacoes", "nonexistent"])
        assert "nonexistent" not in stats

    def test_sha256_is_stable(self, parquet_dir: Path) -> None:
        s1 = collect_table_stats(parquet_dir, ["comunicacoes"])
        s2 = collect_table_stats(parquet_dir, ["comunicacoes"])
        assert s1["comunicacoes"].sha256 == s2["comunicacoes"].sha256


class TestUpdateConsolidationManifest:
    def test_creates_manifest_on_first_run(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        stats = {"comunicacoes": TableStats(rows=100, size_bytes=1024, sha256="abc")}
        update_consolidation_manifest(
            item_id="djen-2026-06-01",
            date_str="2026-06-01",
            schema_version=CURRENT_VERSION,
            table_stats=stats,
            manifest_path=manifest_path,
        )
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert len(data["items"]) == 1
        assert data["items"][0]["item_id"] == "djen-2026-06-01"

    def test_idempotent_on_rerun(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        stats = {"comunicacoes": TableStats(rows=100, size_bytes=1024, sha256="abc")}
        for _ in range(3):
            update_consolidation_manifest(
                item_id="djen-2026-06-01",
                date_str="2026-06-01",
                schema_version=CURRENT_VERSION,
                table_stats=stats,
                manifest_path=manifest_path,
            )
        data = json.loads(manifest_path.read_text())
        assert len(data["items"]) == 1

    def test_accumulates_multiple_dates(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        stats = {"comunicacoes": TableStats(rows=50, size_bytes=512, sha256="def")}
        for date in ["2026-06-01", "2026-06-02", "2026-06-03"]:
            update_consolidation_manifest(
                item_id=f"djen-{date}",
                date_str=date,
                schema_version=CURRENT_VERSION,
                table_stats=stats,
                manifest_path=manifest_path,
            )
        data = json.loads(manifest_path.read_text())
        assert len(data["items"]) == 3
        assert [it["date"] for it in data["items"]] == [
            "2026-06-01",
            "2026-06-02",
            "2026-06-03",
        ]

    def test_items_sorted_by_date(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        stats = {"comunicacoes": TableStats(rows=10, size_bytes=256, sha256="xyz")}
        for date in ["2026-06-03", "2026-06-01", "2026-06-02"]:
            update_consolidation_manifest(
                item_id=f"djen-{date}",
                date_str=date,
                schema_version=CURRENT_VERSION,
                table_stats=stats,
                manifest_path=manifest_path,
            )
        data = json.loads(manifest_path.read_text())
        dates = [it["date"] for it in data["items"]]
        assert dates == sorted(dates)

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "deep" / "nested" / "manifest.json"
        stats = {"comunicacoes": TableStats(rows=1, size_bytes=100, sha256="aaa")}
        update_consolidation_manifest(
            item_id="djen-2026-06-01",
            date_str="2026-06-01",
            schema_version=CURRENT_VERSION,
            table_stats=stats,
            manifest_path=manifest_path,
        )
        assert manifest_path.exists()
