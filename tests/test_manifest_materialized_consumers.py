"""Consumers must observe event-log updates before manifest compaction."""

from pathlib import Path

import duckdb

from scripts.generate_catalog import get_items_from_sync_manifest
from scripts.pipeline.consolidate import load_sync_manifest


def test_consumers_replay_pending_segment_without_csv(tmp_path: Path) -> None:
    """Catalog and consolidation see an uploaded event absent from the base."""
    parquet = tmp_path / "sync-manifest.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            "CREATE TABLE manifest AS SELECT * FROM (VALUES "
            "('TJSP', DATE '2026-01-01', '', 'available', '200', '2026-01-01T00:00:00Z')) "
            "AS t(tribunal, date, ia_status, djen_status, djen_raw, updated_at)"
        )
        con.execute("COPY manifest TO ? (FORMAT PARQUET)", [str(parquet)])
    finally:
        con.close()

    segment_dir = tmp_path / "manifest-log"
    segment_dir.mkdir()
    (segment_dir / "20260102T000000Z-engine-1.csv").write_text(
        "tribunal,date,ia_status,djen_status,djen_raw,updated_at\n"
        "TJSP,2026-01-01,uploaded,available,200,2026-01-02T00:00:00Z\n",
        encoding="utf-8",
    )

    assert get_items_from_sync_manifest(parquet) == ["djen-tjsp-2026"]
    assert load_sync_manifest(parquet)["2026-01-01"][0]["filename"] == "djen-2026-01-01-TJSP.zip"
