#!/usr/bin/env python3
"""Render sync-manifest.csv → sync-manifest.parquet and upload to IA.

Purpose:  Produce a read-optimized Parquet companion to the canonical manifest CSV.
Problem:  The CSV is great for cheap engine appends but expensive to query remotely
          (8MB, full download). Workflows/dashboards only need to read subsets.
Strategy: Merge the upload-backlog delta CSVs (upload-deltas/*.csv on IA) so the
          snapshot reflects confirmed uploads even before the full CSV updates,
          then render to Parquet (columnar + dictionary encoding on the
          high-cardinality `tribunal` column → ~8MB CSV becomes ~1MB) so readers
          can fetch only the row groups they need via DuckDB httpfs. Writes still
          flow through the CSV — this is a derived read replica.
Status:   production — runs every 30 min via render-manifest-parquet.yml.
"""

from __future__ import annotations

# Safely reconfigure standard output and standard error encoding error handling on Windows
import contextlib
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

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


def render_parquet(csv_path: Path, delta_urls: list[str], *, write_back: bool = False) -> Path:
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

    # Apply each delta: mark uploaded rows and absent (DJEN 404) rows
    merged_uploaded = 0
    merged_absent = 0
    merged_confirmed = 0
    for url in delta_urls:
        try:
            delta_rows = con.execute(
                f"""
                SELECT tribunal::VARCHAR, date::DATE,
                       ia_status::VARCHAR, djen_status::VARCHAR, updated_at::VARCHAR
                FROM read_csv_auto('{url}', header=true,
                    types={{'tribunal':'VARCHAR','date':'DATE','ia_status':'VARCHAR',
                            'djen_status':'VARCHAR','updated_at':'VARCHAR'}})
                """
            ).fetchall()
        except Exception as exc:
            print(f"  warning: could not read delta {url}: {exc}")
            continue
        for tribunal, date, ia_status, djen_status, updated_at in delta_rows:
            if ia_status == "uploaded":
                con.execute(
                    """
                    UPDATE manifest SET ia_status = 'uploaded', updated_at = ?
                    WHERE tribunal = ? AND date = ?
                      AND (ia_status IS NULL OR ia_status != 'uploaded')
                    """,
                    [updated_at, tribunal, date],
                )

                merged_uploaded += 1
            elif djen_status == "absent":
                con.execute(
                    """
                    UPDATE manifest SET djen_status = 'absent', updated_at = ?
                    WHERE tribunal = ? AND date = ?
                      AND (djen_status IS NULL OR djen_status != 'absent')
                      AND (ia_status IS NULL OR ia_status != 'uploaded')
                    """,
                    [updated_at, tribunal, date],
                )
                merged_absent += 1
            elif djen_status == "confirmed":
                con.execute(
                    """
                    UPDATE manifest SET djen_status = 'confirmed', updated_at = ?
                    WHERE tribunal = ? AND date = ?
                      AND djen_status = 'available'
                    """,
                    [updated_at, tribunal, date],
                )
                merged_confirmed += 1

    if delta_urls:
        print(
            f"  merged {merged_uploaded} uploaded + "
            f"{merged_absent} absent + "
            f"{merged_confirmed} confirmed rows from "
            f"{len(delta_urls)} delta file(s)"
        )

    con.execute(f"COPY manifest TO '{LOCAL_PARQUET}' (FORMAT PARQUET, COMPRESSION ZSTD)")

    _print_merge_stats(con)
    if write_back:
        write_back_csv(con)
    return LOCAL_PARQUET


def _print_merge_stats(con: duckdb.DuckDBPyConnection) -> None:
    """Show how the delta merge reshaped the manifest vs the raw CSV base.

    The headline number is rows the deltas reclassified to ``absent`` while the
    HTTP code stayed ``200`` — genuine "Sem comunicações" absents the canonical
    CSV still mislabels as ``available`` (see docs/planning/manifest-source-of-truth.md).
    """
    absent_200 = con.execute(
        "SELECT count(*) FROM manifest WHERE djen_status = 'absent' AND djen_raw = '200'"
    ).fetchone()[0]
    pending = con.execute(
        """SELECT count(*) FROM manifest
           WHERE djen_status IN ('available', 'confirmed')
             AND (ia_status IS NULL OR ia_status != 'uploaded')"""
    ).fetchone()[0]
    print(f"  merged manifest: {absent_200:,} rows are absent-with-HTTP-200 (Sem comunicações)")
    print(f"  pending uploads after merge: {pending:,}")


def write_back_csv(con: duckdb.DuckDBPyConnection) -> Path:
    """Export the merged manifest back to the canonical CSV layout.

    This is the *compaction write-back* (Phase 1 of
    docs/planning/manifest-source-of-truth.md): the merge result — which folds
    the delta corrections in — becomes the new canonical CSV, so the CSV stops
    drifting behind the Parquet. Re-applying deltas over an already-corrected
    CSV is idempotent, so deltas are NOT pruned here (kept simple + safe).
    """
    # Bare-empty fields (",,") to match the canonical CSV exactly — COALESCE to
    # '' + the default quoting would emit `""`; letting NULLs flow with the
    # default NULLSTR='' writes bare empties like the engine's own to_csv().
    con.execute(
        f"""
        COPY (
            SELECT
                tribunal,
                strftime(date, '%Y-%m-%d') AS date,
                ia_status,
                djen_status,
                djen_raw,
                updated_at
            FROM manifest
            ORDER BY tribunal, date
        ) TO '{LOCAL_CSV}' (FORMAT CSV, HEADER)
        """
    )
    print(f"  wrote back merged CSV: {LOCAL_CSV} ({LOCAL_CSV.stat().st_size:,} bytes)")
    return LOCAL_CSV


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


async def upload(path: Path, target: str) -> None:
    auth = (
        f"LOW {os.environ['IAS3_ACCESS_KEY']}:{os.environ['IAS3_SECRET_KEY']}"
        if os.environ.get("IAS3_ACCESS_KEY") and os.environ.get("IAS3_SECRET_KEY")
        else None
    )
    if not auth:
        print(f"No IA credentials — skipping upload of {target}")
        return

    async with create_upload_client(auth) as client:
        ok = await upload_to_ia(client, IA_ITEM, path, target)
        print(f"{target}: {'uploaded' if ok else 'upload failed'}")


def main() -> None:
    # Phase 1 (docs/planning/manifest-source-of-truth.md): when MANIFEST_COMPACT_WRITEBACK
    # is set, the merged manifest is written back to the canonical CSV so it stops
    # drifting behind the Parquet. Default OFF — enabling is a deliberate op step
    # (writes the shared CSV; ideally run when the engine isn't appending).
    # MANIFEST_DRY_RUN renders + reports locally without touching IA.
    write_back = _env_truthy("MANIFEST_COMPACT_WRITEBACK")
    dry_run = _env_truthy("MANIFEST_DRY_RUN")

    csv = ensure_csv()
    print(f"CSV: {csv} ({csv.stat().st_size:,} bytes)")
    delta_urls = fetch_delta_urls()
    print(f"Delta files found: {len(delta_urls)}")
    parquet = render_parquet(csv, delta_urls, write_back=write_back)
    uploaded_count = duckdb.execute(
        f"SELECT count(*) FROM read_parquet('{parquet}') WHERE ia_status = 'uploaded'"
    ).fetchone()[0]
    print(f"Parquet: {parquet} ({parquet.stat().st_size:,} bytes)")
    print(f"  ia_status=uploaded in parquet: {uploaded_count}")
    print(
        f"  write-back: {'ON' if write_back else 'off'}  |  dry-run: {'ON' if dry_run else 'off'}"
    )

    if dry_run:
        print("Dry run — no IA uploads.")
        return

    asyncio.run(upload(parquet, IA_TARGET))
    if write_back:
        asyncio.run(upload(LOCAL_CSV, "sync-manifest.csv"))


if __name__ == "__main__":
    main()
