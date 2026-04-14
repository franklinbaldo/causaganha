#!/usr/bin/env python3
"""Render sync-manifest.csv → sync-manifest.parquet and upload to IA.

The Parquet artifact is a read-optimized companion to the canonical CSV.
Engine writes still go through the CSV (cheap appends); workflows and
dashboards that only need to QUERY the manifest can fetch this Parquet
via DuckDB httpfs and pull only the row groups they care about.

Typical size reduction: 8MB CSV → ~1MB Parquet (columnar + dictionary
encoding on the high-cardinality `tribunal` column).
"""

from __future__ import annotations

import asyncio
import os
import urllib.request
from pathlib import Path

import duckdb

from causaganha.pipeline.ia_s3 import create_upload_client, upload_to_ia


MANIFEST_CSV_URL = "https://archive.org/download/causaganha-dashboard/sync-manifest.csv"
LOCAL_CSV = Path("data/sync-manifest.csv")
LOCAL_PARQUET = Path("data/sync-manifest.parquet")
IA_ITEM = "causaganha-dashboard"
IA_TARGET = "sync-manifest.parquet"


def ensure_csv() -> Path:
    if LOCAL_CSV.exists():
        return LOCAL_CSV
    LOCAL_CSV.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading manifest from {MANIFEST_CSV_URL}...")
    with urllib.request.urlopen(MANIFEST_CSV_URL, timeout=120) as resp:
        LOCAL_CSV.write_bytes(resp.read())
    return LOCAL_CSV


def render_parquet(csv_path: Path) -> Path:
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (
          SELECT
            tribunal::VARCHAR AS tribunal,
            date::DATE AS date,
            ia_status::VARCHAR AS ia_status,
            djen_status::VARCHAR AS djen_status,
            djen_raw::VARCHAR AS djen_raw,
            updated_at::VARCHAR AS updated_at
          FROM read_csv_auto(
            '{csv_path}',
            header=true,
            types={{'tribunal':'VARCHAR','date':'DATE','ia_status':'VARCHAR','djen_status':'VARCHAR','djen_raw':'VARCHAR','updated_at':'VARCHAR'}}
          )
        )
        TO '{LOCAL_PARQUET}' (FORMAT PARQUET, COMPRESSION ZSTD);
        """
    )
    return LOCAL_PARQUET


async def upload(parquet_path: Path) -> None:
    auth = (
        f"LOW {os.environ['IAS3_ACCESS_KEY']}:{os.environ['IAS3_SECRET_KEY']}"
        if os.environ.get("IAS3_ACCESS_KEY") and os.environ.get("IAS3_SECRET_KEY")
        else None
    )
    if not auth:
        print("No IA credentials — skipping upload")
        return

    async with create_upload_client(auth) as client:
        ok = await upload_to_ia(client, IA_ITEM, parquet_path, IA_TARGET)
        print("uploaded" if ok else "upload failed")


def main() -> None:
    csv = ensure_csv()
    print(f"CSV: {csv} ({csv.stat().st_size:,} bytes)")
    parquet = render_parquet(csv)
    print(f"Parquet: {parquet} ({parquet.stat().st_size:,} bytes)")
    asyncio.run(upload(parquet))


if __name__ == "__main__":
    main()
