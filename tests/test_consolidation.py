"""Test parallel Parquet export with local ZIPs."""

import json
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ibis
import pytest
import structlog

from scripts.pipeline.consolidate import (
    TABLES,
    _load_and_transform,
    extract_json_from_zip,
    init_tables,
)


logger = structlog.get_logger()


def _write_ndjson_from_zips(test_zip_dir: Path, ndjson_dir: Path) -> int:
    """Extract JSON from ZIPs and write NDJSON files for _load_and_transform."""
    total_records = 0
    for zip_file in sorted(test_zip_dir.glob("*.zip")):
        tribunal = zip_file.name.split("-")[-1].replace(".zip", "")

        records = extract_json_from_zip(zip_file)
        if not records:
            continue

        total_records += len(records)

        ndjson_path = ndjson_dir / f"{tribunal}__{zip_file.stem}.ndjson"
        with ndjson_path.open("w") as f:
            for rec in records:
                if isinstance(rec, dict):
                    f.write(json.dumps(rec, default=str) + "\n")

    return total_records


def test_parallel_export():
    """Test parallel Parquet export with local test ZIPs."""
    test_zip_dir = Path("test_zips")

    if not test_zip_dir.exists():
        pytest.skip("test_zips directory not found")

    # Set up test database
    con = ibis.duckdb.connect()
    init_tables(con)

    # Extract ZIPs to NDJSON and load via _load_and_transform
    with tempfile.TemporaryDirectory() as ndjson_tmpdir:
        ndjson_dir = Path(ndjson_tmpdir)
        total_records = _write_ndjson_from_zips(test_zip_dir, ndjson_dir)

        if total_records == 0:
            pytest.skip("no records extracted from test ZIPs")

        _load_and_transform(con, ndjson_dir, item_id="test-item")

    # Now test the parallel export

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()

        # Helper function (same as in consolidate.py)
        def _export_and_upload_table(table_name: str, con, output_dir: Path, *, _dry_run: bool):
            t = con.table(table_name)
            count = t.count().to_pandas()
            if count == 0:
                return False, 0, 0

            output_path = output_dir / f"{table_name}.parquet"
            start = time.time()
            con.raw_sql(
                f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)",
            )
            elapsed = time.time() - start
            return True, 1, elapsed

        # Test SEQUENTIAL export first (baseline)
        seq_exported = 0
        for table_name in TABLES:
            success, _, _elapsed = _export_and_upload_table(
                table_name, con, output_dir, _dry_run=True
            )
            if success:
                seq_exported += 1
        assert seq_exported > 0, "Sequential export should export at least one table"

        # Clean output dir for parallel test
        for f in output_dir.glob("*.parquet"):
            f.unlink()

        # Test PARALLEL export
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(
                    _export_and_upload_table, table_name, con, output_dir, _dry_run=True
                )
                for table_name in TABLES
            ]
            par_exported = 0
            for future in futures:
                success, _, _ = future.result()
                if success:
                    par_exported += 1
        par_time = time.time() - start_time

        assert par_exported == seq_exported, (
            f"Parallel export ({par_exported}) should match sequential ({seq_exported})"
        )
        assert par_time > 0, "Parallel export time should be positive"
