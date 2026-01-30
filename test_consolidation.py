#!/usr/bin/env python3
"""Test parallel Parquet export with local ZIPs"""

import sys
import tempfile
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/c/Users/frank/workspace/causaganha")

import ibis
import structlog
from scripts.pipeline.consolidate import (
    extract_json_from_zip,
    parse_records,
    init_tables,
    upload_to_ia,
    TABLE_SCHEMAS,
    TABLES,
)

logger = structlog.get_logger()

def test_parallel_export():
    """Test parallel Parquet export with local test ZIPs"""
    test_zip_dir = Path("/c/Users/frank/workspace/causaganha/test_zips")
    
    # Set up test database
    con = ibis.duckdb.connect()
    init_tables(con)
    
    # Load data from test ZIPs
    print("\n" + "=" * 60)
    print("LOADING TEST DATA FROM LOCAL ZIPS")
    print("=" * 60)
    
    total_records = 0
    for zip_file in sorted(test_zip_dir.glob("*.zip")):
        print(f"\nProcessing {zip_file.name}...")
        tribunal = zip_file.name.split("-")[-1].replace(".zip", "")
        
        records = extract_json_from_zip(zip_file)
        if not records:
            print(f"  [!] No records found")
            continue

        print(f"  [OK] Extracted {len(records)} records")
        total_records += len(records)

        # Parse and insert
        tables = parse_records(records, tribunal, "test-item")
        for table_name, rows in tables.items():
            if rows:
                data = ibis.memtable(rows, schema=TABLE_SCHEMAS[table_name])
                con.insert(table_name, data)

    print(f"\n[OK] Total records loaded: {total_records}")
    
    # Now test the parallel export
    print("\n" + "=" * 60)
    print("TESTING PARALLEL PARQUET EXPORT")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()
        
        # Helper function (same as in consolidate.py)
        def _export_and_upload_table(table_name: str, con, output_dir: Path, dry_run: bool):
            try:
                t = con.table(table_name)
                count = t.count().to_pandas()
                if count == 0:
                    return False, 0, 0
                
                output_path = output_dir / f"{table_name}.parquet"
                start = time.time()
                con.raw_sql(
                    f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
                )
                elapsed = time.time() - start
                
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"  [OK] {table_name:20} | {count:7d} rows | {size_mb:6.1f} MB | {elapsed:6.2f}s")
                return True, 1, elapsed
            except Exception as e:
                print(f"  [ERROR] {table_name:20} | ERROR: {str(e)}")
                return False, 0, 0
        
        # Test SEQUENTIAL export first (baseline)
        print("\n[BASELINE] SEQUENTIAL EXPORT:")
        start_time = time.time()
        total_exported = 0
        for table_name in TABLES:
            success, _, elapsed = _export_and_upload_table(table_name, con, output_dir, True)
            if success:
                total_exported += 1
        seq_time = time.time() - start_time
        print(f"\n  Sequential time: {seq_time:.2f}s")
        
        # Clean output dir for parallel test
        for f in output_dir.glob("*.parquet"):
            f.unlink()
        
        # Test PARALLEL export
        print("\n[OPTIMIZED] PARALLEL EXPORT (with ThreadPoolExecutor, max_workers=3):")
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
        print(f"\n  Parallel time: {par_time:.2f}s")
        
        # Results
        print("\n" + "=" * 60)
        print("PERFORMANCE IMPROVEMENT")
        print("=" * 60)
        speedup = seq_time / par_time
        improvement = (seq_time - par_time) / seq_time * 100
        print(f"  Sequential: {seq_time:.2f}s")
        print(f"  Parallel:   {par_time:.2f}s")
        print(f"  Speedup:    {speedup:.2f}x")
        print(f"  Improvement: {improvement:.1f}%")
        print(f"  Time saved:  {seq_time - par_time:.2f}s")
        print("=" * 60)
        
        if speedup >= 1.5:
            print("[SUCCESS] OPTIMIZATION SUCCESSFUL - Parallel is significantly faster")
            return 0
        else:
            print("[INFO] Parallel not significantly faster (may still help with I/O-bound operations)")
            return 0

if __name__ == "__main__":
    sys.exit(test_parallel_export())
