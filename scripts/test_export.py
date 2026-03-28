from datetime import timezone
import pyarrow.parquet as pq
import traceback
#!/usr/bin/env python3
"""Test Parquet export functionality."""

import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from causaganha.pipeline.parquet_export import ExportConfig, ParquetExporter
from causaganha.storage.connection import get_connection


async def test_export() -> None:
    """Test exporting data to Parquet."""
    con = get_connection()
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Initialize exporter
    config = ExportConfig(output_dir=Path("data/exports"))
    exporter = ParquetExporter(con, config)

    # Test export for each tribunal
    tribunals = ["TJRO", "TJSP", "TJAC"]

    for tribunal in tribunals:
        try:
            file_path, _row_count = await exporter.export_day_tribunal(
                partition_date=yesterday,
                tribunal=tribunal,
            )

            # Check file was created
            if file_path.exists():
                file_path.stat().st_size / (1024 * 1024)

                # Try reading the Parquet file

                table = pq.read_table(file_path)
                export_frame = table.to_pandas()
                if len(export_frame) > 0:
                    pass
            else:
                pass

        except Exception:

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_export())
