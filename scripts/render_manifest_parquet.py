#!/usr/bin/env python3
"""Render sync-manifest.csv → sync-manifest.parquet and upload to IA.

The Parquet artifact is a read-optimized companion to the canonical CSV.
Engine writes still go through the CSV (cheap appends); workflows and
dashboards that only need to QUERY the manifest can fetch this Parquet
via DuckDB httpfs and pull only the row groups they care about.

Delta CSVs written by the upload-backlog drain (upload-deltas/*.csv on IA)
are merged in before rendering so the parquet reflects confirmed uploads
even before the full sync-manifest.csv is updated.

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
IA_DELTA_INDEX_URL = "https://archive.org/download/causaganha-dashboard/"
LOCAL_CSV = Path("data/sync-manifest.csv")
LOCAL_PARQUET = Path("data/sync-manifest.parquet")
IA_ITEM = "causaganha-dashboard"
IA_TARGET = "sync-manifest.parquet"


def ensure_csv() -> Path:
    """Always fetch fresh from IA — local CSV may be stale from another workflow."""
    LOCAL_CSV.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading manifest from {MANIFEST_CSV_URL}...")
    with urllib.request.urlopen(MANIFEST_CSV_URL, timeout=120) as resp:
        LOCAL_CSV.write_bytes(resp.read())
    print(f"  fetched {LOCAL_CSV.stat().st_size:,} bytes")
    return LOCAL_CSV


def fetch_delta_urls() -> list[str]:
    """List upload-delta CSV URLs from the IA item index."""
    base = "https://archive.org/download/causaganha-dashboard"
    try:
        with urllib.request.urlopen(IA_DELTA_INDEX_URL, timeout=30) as resp:
            html = resp.read().decode()
    except Exception as exc:
        print(f"  warning: could not fetch delta index: {exc}")
        return []
    urls = []
    for line in html.splitlines():
        if "upload-deltas-" not in line or ".csv" not in line:
            continue
        start = line.find('href="') + 6
        end = line.find('"', start)
        if start > 5 and end > start:
            fname = line[start:end]
            urls.append(f"{base}/{fname}")
    return urls


def render_parquet(csv_path: Path, delta_urls: list[str]) -> Path:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")

    # Load base manifest
    con.execute(
        f"""
        CREATE TABLE manifest AS
        SELECT
            tribunal::VARCHAR AS tribunal,
            date::DATE        AS date,
            ia_status::VARCHAR AS ia_status,
            djen_status::VARCHAR AS djen_status,
            djen_raw::VARCHAR AS djen_raw,
            updated_at::VARCHAR AS updated_at
        FROM read_csv_auto(
            '{csv_path}',
            header=true,
            types={{'tribunal':'VARCHAR','date':'DATE','ia_status':'VARCHAR',
                    'djen_status':'VARCHAR','djen_raw':'VARCHAR','updated_at':'VARCHAR'}}
        )
        """
    )

    # Apply each delta: mark rows as uploaded where the delta says so
    merged = 0
    for url in delta_urls:
        try:
            rows = con.execute(
                f"""
                SELECT tribunal::VARCHAR, date::DATE, updated_at::VARCHAR
                FROM read_csv_auto('{url}', header=true,
                    types={{'tribunal':'VARCHAR','date':'DATE',
                            'ia_status':'VARCHAR','updated_at':'VARCHAR'}})
                WHERE ia_status = 'uploaded'
                """
            ).fetchall()
        except Exception as exc:
            print(f"  warning: could not read delta {url}: {exc}")
            continue
        for tribunal, date, updated_at in rows:
            con.execute(
                """
                UPDATE manifest SET ia_status = 'uploaded', updated_at = ?
                WHERE tribunal = ? AND date = ? AND (ia_status IS NULL OR ia_status != 'uploaded')
                """,
                [updated_at, tribunal, date],
            )
        merged += len(rows)

    if delta_urls:
        print(f"  merged {merged} delta rows from {len(delta_urls)} delta file(s)")

    con.execute(f"COPY manifest TO '{LOCAL_PARQUET}' (FORMAT PARQUET, COMPRESSION ZSTD)")
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
    delta_urls = fetch_delta_urls()
    print(f"Delta files found: {len(delta_urls)}")
    parquet = render_parquet(csv, delta_urls)
    uploaded_count = duckdb.execute(
        f"SELECT count(*) FROM read_parquet('{parquet}') WHERE ia_status = 'uploaded'"
    ).fetchone()[0]
    print(f"Parquet: {parquet} ({parquet.stat().st_size:,} bytes)")
    print(f"  ia_status=uploaded in parquet: {uploaded_count}")
    asyncio.run(upload(parquet))


if __name__ == "__main__":
    main()
