#!/usr/bin/env python3
"""Test Parquet export functionality."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from causaganha.pipeline.parquet_export import ExportConfig, ParquetExporter
from causaganha.storage.connection import get_connection


async def test_export():
    """Test exporting data to Parquet."""
    con = get_connection()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Testing Parquet export for date: {yesterday}")
    print("=" * 60)

    # Initialize exporter
    config = ExportConfig(output_dir=Path("data/exports"))
    exporter = ParquetExporter(con, config)

    # Test export for each tribunal
    tribunals = ["TJRO", "TJSP", "TJAC"]

    for tribunal in tribunals:
        print(f"\n📦 Exporting {tribunal}...")

        try:
            file_path, row_count = await exporter.export_day_tribunal(
                partition_date=yesterday,
                tribunal=tribunal,
            )

            # Check file was created
            if file_path.exists():
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                print("   ✅ Success!")
                print(f"   - File: {file_path.name}")
                print(f"   - Path: {file_path}")
                print(f"   - Rows: {row_count}")
                print(f"   - Size: {file_size_mb:.2f} MB")

                # Try reading the Parquet file
                import pyarrow.parquet as pq

                table = pq.read_table(file_path)
                print(f"   - Columns: {table.schema.names}")
                print("   - First row sample:")
                df = table.to_pandas()
                if len(df) > 0:
                    print(f"     numero_processo: {df.iloc[0]['numero_processo']}")
                    print(f"     tribunal: {df.iloc[0]['sigla_tribunal']}")
                    print(f"     winner_oab: {df.iloc[0]['winner_lawyer_oab']}")
                    print(f"     confidence: {df.iloc[0]['confidence_score']:.2f}")
            else:
                print("   ❌ File not created!")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Export test complete!")


if __name__ == "__main__":
    asyncio.run(test_export())
