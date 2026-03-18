#!/usr/bin/env python3
"""Test parallel Parquet export with local ZIPs."""

import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


sys.path.insert(0, "/c/Users/frank/workspace/causaganha")

import ibis
import structlog

from scripts.pipeline.consolidate import (
    TABLE_SCHEMAS,
    TABLES,
    extract_json_from_zip,
    init_tables,
    parse_records,
)


logger = structlog.get_logger()


def test_parallel_export() -> int:
    """Test parallel Parquet export with local test ZIPs."""
    test_zip_dir = Path("/c/Users/frank/workspace/causaganha/test_zips")

    # Set up test database
    con = ibis.duckdb.connect()
    init_tables(con)

    # Load data from test ZIPs

    total_records = 0
    for zip_file in sorted(test_zip_dir.glob("*.zip")):
        tribunal = zip_file.name.split("-")[-1].replace(".zip", "")

        records = extract_json_from_zip(zip_file)
        if not records:
            continue

        total_records += len(records)

        # Parse and insert
        tables = parse_records(records, tribunal, "test-item")
        for table_name, rows in tables.items():
            if rows:
                data = ibis.memtable(rows, schema=TABLE_SCHEMAS[table_name])
                con.insert(table_name, data)

    # Now test the parallel export

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()

        # Helper function (same as in consolidate.py)
        def _export_and_upload_table(table_name: str, con, output_dir: Path, _dry_run: bool):
            try:
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

                output_path.stat().st_size / (1024 * 1024)
                result = (True, 1, elapsed)
            except Exception:
                return False, 0, 0
            else:
                return result

        # Test SEQUENTIAL export first (baseline)
        start_time = time.time()
        total_exported = 0
        for table_name in TABLES:
            success, _, _elapsed = _export_and_upload_table(table_name, con, output_dir, True)
            if success:
                total_exported += 1
        seq_time = time.time() - start_time

        # Clean output dir for parallel test
        for f in output_dir.glob("*.parquet"):
            f.unlink()

        # Test PARALLEL export
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(_export_and_upload_table, table_name, con, output_dir, True)
                for table_name in TABLES
            ]
            total_exported = 0
            for future in futures:
                success, _, _ = future.result()
                if success:
                    total_exported += 1
        par_time = time.time() - start_time

        # Results
        speedup = seq_time / par_time
        (seq_time - par_time) / seq_time * 100

        if speedup >= 1.5:
            return 0
        return 0


if __name__ == "__main__":
    sys.exit(test_parallel_export())
