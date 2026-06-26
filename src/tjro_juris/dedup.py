"""Deduplication utilities for TJRO JURIS parquet files."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.parquet as pq


if TYPE_CHECKING:
    from pathlib import Path


def consolidate_year(parquet_files: list[Path], output: Path) -> int:
    """Dedup by id_documento across monthly parquets for a year. Return count."""
    if not parquet_files:
        return 0

    tables = [pq.read_table(p) for p in parquet_files]
    combined = pa.concat_tables(tables, promote_options="default")

    if "id_documento" in combined.schema.names:
        # Convert to Python for dedup via dict, then back to Arrow
        col = combined.column("id_documento").to_pylist()
        seen: set = set()
        keep: list[bool] = []
        for val in col:
            if val is None or val in seen:
                keep.append(False)
            else:
                seen.add(val)
                keep.append(True)
        mask = pa.array(keep, type=pa.bool_())
        combined = combined.filter(mask)

    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(combined, output)
    return combined.num_rows
