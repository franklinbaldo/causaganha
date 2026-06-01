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
import ibis

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


def _apply_deltas(con: duckdb.DuckDBPyConnection, delta_urls: list[str]) -> tuple[int, int, int]:
    """Merge the upload-delta corrections into the ``manifest`` table in place.

    Stages every delta row into one table (resilient per-file load), then applies
    the corrections as set-based UPDATEs instead of a row-by-row Python loop.
    Three independent signals; applying uploaded first means an archived item is
    never also flagged absent. This is deterministic — the old per-row loop's
    result for a key with conflicting deltas depended on file/row ordering
    (see docs/planning/manifest-source-of-truth.md). Returns the count of rows
    actually updated per signal (uploaded, absent, confirmed).
    """
    con.execute(
        """
        CREATE TABLE deltas (
            tribunal VARCHAR, date DATE, ia_status VARCHAR,
            djen_status VARCHAR, updated_at VARCHAR
        )
        """
    )
    for url in delta_urls:
        try:
            con.execute(
                f"""
                INSERT INTO deltas
                SELECT tribunal::VARCHAR, date::DATE,
                       ia_status::VARCHAR, djen_status::VARCHAR, updated_at::VARCHAR
                FROM read_csv_auto('{url}', header=true,
                    types={{'tribunal':'VARCHAR','date':'DATE','ia_status':'VARCHAR',
                            'djen_status':'VARCHAR','updated_at':'VARCHAR'}})
                """
            )
        except (duckdb.Error, OSError) as exc:
            print(f"  warning: could not read delta {url}: {exc}")

    merged_uploaded = con.execute(
        """
        UPDATE manifest SET ia_status = 'uploaded', updated_at = d.updated_at
        FROM (
            SELECT tribunal, date, max(updated_at) AS updated_at
            FROM deltas WHERE ia_status = 'uploaded' GROUP BY tribunal, date
        ) d
        WHERE manifest.tribunal = d.tribunal AND manifest.date = d.date
          AND (manifest.ia_status IS NULL OR manifest.ia_status != 'uploaded')
        """
    ).fetchone()[0]

    merged_absent = con.execute(
        """
        UPDATE manifest SET djen_status = 'absent', updated_at = d.updated_at
        FROM (
            SELECT tribunal, date, max(updated_at) AS updated_at
            FROM deltas WHERE djen_status = 'absent' GROUP BY tribunal, date
        ) d
        WHERE manifest.tribunal = d.tribunal AND manifest.date = d.date
          AND (manifest.djen_status IS NULL OR manifest.djen_status != 'absent')
          AND (manifest.ia_status IS NULL OR manifest.ia_status != 'uploaded')
        """
    ).fetchone()[0]

    merged_confirmed = con.execute(
        """
        UPDATE manifest SET djen_status = 'confirmed', updated_at = d.updated_at
        FROM (
            SELECT tribunal, date, max(updated_at) AS updated_at
            FROM deltas WHERE djen_status = 'confirmed' GROUP BY tribunal, date
        ) d
        WHERE manifest.tribunal = d.tribunal AND manifest.date = d.date
          AND manifest.djen_status = 'available'
        """
    ).fetchone()[0]

    if delta_urls:
        print(
            f"  merged {merged_uploaded} uploaded + "
            f"{merged_absent} absent + "
            f"{merged_confirmed} confirmed rows from "
            f"{len(delta_urls)} delta file(s)"
        )
    return merged_uploaded, merged_absent, merged_confirmed


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

    _apply_deltas(con, delta_urls)

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

    Self-consistency: the delta merge only flips ``djen_status`` to ``absent``
    and leaves ``djen_raw='200'`` behind, so the row contradicts itself —
    ``interpret_djen_raw('200')`` derives ``available``. We rewrite that raw to
    the ``no_publications`` sentinel (already in ``ABSENT_CODES`` → ``absent``)
    so the row re-derives to ``absent`` no matter who reads it, instead of
    relying on every consumer trusting the stored ``djen_status`` over the raw.

    CSV vocabulary: ``confirmed`` is a parquet/drain-only refinement of
    ``available``; the CSV consumers don't know it (``entries_needing_upload``
    selects only ``available`` and ``_categorize`` buckets ``confirmed`` as
    ``unknown``), so a confirmed-but-not-uploaded row would drop out of the
    CSV upload/check flow. Normalize it back to ``available`` for the CSV.
    """
    manifest = ibis.duckdb.from_connection(con).table("manifest")
    corrected = manifest.mutate(
        date=manifest.date.strftime("%Y-%m-%d"),
        djen_status=ibis.cases(
            (manifest.djen_status == "confirmed", "available"),
            else_=manifest.djen_status,
        ),
        djen_raw=ibis.cases(
            (
                (manifest.djen_status == "absent")
                & ((manifest.djen_raw == "200") | manifest.djen_raw.startswith("200:")),
                "no_publications",
            ),
            else_=manifest.djen_raw,
        ),
    ).select("tribunal", "date", "ia_status", "djen_status", "djen_raw", "updated_at")

    # pandas to_csv renders NULL/empty as bare "" fields (na_rep=''), matching
    # SyncManifest.to_csv() byte-for-byte — no DuckDB COPY quoting/NULLSTR fiddling.
    corrected.order_by(["tribunal", "date"]).to_pandas().to_csv(LOCAL_CSV, index=False)
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
    # drifting behind the Parquet. Default OFF — enabling is a deliberate op step.
    # REQUIRED ordering: stop the engine → run write-back → restart the engine.
    # A running engine holds the legacy rows as 'available' in memory and never
    # re-checks rows that already have a djen_status, so its periodic 10-min IA
    # upload would clobber the corrected CSV straight back to available-200.
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
