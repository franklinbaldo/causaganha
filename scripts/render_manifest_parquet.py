#!/usr/bin/env python3
"""Compact the manifest event log into sync-manifest.parquet and upload to IA.

Phase 3 of docs/planning/manifest-source-of-truth.md (§4.3, §5): this is the
single-writer *compaction* job. The canonical CSV is retired — the parquet
base is the sole source of truth, with no CSV bootstrap fallback.

Base:     the current ``sync-manifest.parquet`` on IA (the compacted base).
          If it does not exist, compaction cannot proceed (no CSV fallback).
Events:   1. legacy ``upload-deltas-*.csv`` files (5-col, drain/probe of old
             deploys) — merged via the historical set-based rules;
          2. new ``manifest-log/*.csv`` segments (6-col upsert events from
             engine/drain/probe) — merged field-by-field, last-write-wins
             by ``updated_at``.
Output:   a NEW ``sync-manifest.parquet`` base uploaded atomically (single
          PUT replaces the object), after which absorbed manifest-log
          segments are pruned — moved to ``manifest-log/compacted/`` for
          audit/replay, never deleted outright. A CSV export can still be
          produced on demand via ``MANIFEST_COMPACT_WRITEBACK`` (see
          ``write_back_csv``), but it is no longer read by anything.

Correctness: ``djen_raw`` stays the raw transport code. Rows whose verdict is
``absent`` while the raw still says ``200`` (legacy body-blind checker) are
rewritten to the ``no_publications`` sentinel so the row re-derives to absent
from the raw alone.

Status:  production — runs every 30 min via render-manifest-parquet.yml
         (serialized by the workflow ``concurrency:`` group, per plan §4.3).
"""

from __future__ import annotations

import asyncio

# Safely reconfigure standard output and standard error encoding error handling on Windows
import contextlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import duckdb
import httpx
import ibis
import tenacity

from causaganha.pipeline.ia_s3 import create_upload_client, upload_to_ia

for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")


IA_ITEM = "causaganha-dashboard"
MANIFEST_PARQUET_URL = f"https://archive.org/download/{IA_ITEM}/sync-manifest.parquet"
IA_FILES_METADATA_URL = f"https://archive.org/metadata/{IA_ITEM}/files"
IA_DOWNLOAD_BASE = f"https://archive.org/download/{IA_ITEM}"
IA_S3_ITEM_URL = f"https://s3.us.archive.org/{IA_ITEM}"
SEGMENT_DIR = "manifest-log"
SEGMENT_COMPACTED_DIR = "manifest-log/compacted"

LOCAL_CSV = Path("data/sync-manifest.csv")
LOCAL_BASE_PARQUET = Path("data/sync-manifest-base.parquet")
LOCAL_PARQUET = Path("data/sync-manifest.parquet")
LOCAL_SEGMENT_DIR = Path("data/manifest-log")
IA_TARGET = "sync-manifest.parquet"

MANIFEST_COLUMNS = "tribunal,date,ia_status,djen_status,djen_raw,updated_at"
_CSV_TYPES = (
    "{'tribunal':'VARCHAR','date':'DATE','ia_status':'VARCHAR',"
    "'djen_status':'VARCHAR','djen_raw':'VARCHAR','updated_at':'VARCHAR'}"
)


# ---------------------------------------------------------------------------
# Fetch base + event sources from IA
# ---------------------------------------------------------------------------

# archive.org occasionally times out (slow handshake, transient unreachability)
# well within a single 30-min compaction cycle. Retry a few times before
# treating it as "no base available" / "no file listing" — those are for the
# genuinely-missing case, not a one-off network blip. This policy is only for
# the two single, load-bearing reads (base parquet, file listing) — it is
# deliberately NOT reused for per-segment downloads below, see
# _RETRY_IA_SEGMENT.
_RETRY_IA_GET = tenacity.retry(
    retry=tenacity.retry_if_exception_type((urllib.error.URLError, OSError)),
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=5, min=5, max=30),
    reraise=True,
)

# Segments are downloaded one by one in a loop (download_segments below); the
# generous _RETRY_IA_GET policy applied per-segment would multiply the whole
# compaction cycle's duration during a real outage (N segments x 3 attempts x
# up to 30s backoff each). Keep it cheap and bounded instead — a failed
# segment is simply left for the next scheduled run either way — and pair it
# with a consecutive-failure circuit breaker in download_segments so a full
# IA outage aborts quickly rather than working through every segment.
_RETRY_IA_SEGMENT = tenacity.retry(
    retry=tenacity.retry_if_exception_type((urllib.error.URLError, OSError)),
    stop=tenacity.stop_after_attempt(2),
    wait=tenacity.wait_exponential(multiplier=2, min=2, max=4),
    reraise=True,
)

# After this many consecutive segment-download failures, download_segments
# stops attempting the rest of the batch — IA is very likely down entirely,
# and retrying every remaining segment would only stretch out the cycle for
# no benefit; they're picked up by the next scheduled run instead.
SEGMENT_CIRCUIT_BREAKER_THRESHOLD = 2


@_RETRY_IA_GET
def _urlopen_bytes(url: str, *, timeout: int) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


@_RETRY_IA_SEGMENT
def _urlopen_bytes_segment(url: str, *, timeout: int) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def ensure_base_parquet() -> Path | None:
    """Fetch the current parquet base from IA; None when it doesn't exist yet."""
    LOCAL_BASE_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading parquet base from {MANIFEST_PARQUET_URL}...")
    try:
        LOCAL_BASE_PARQUET.write_bytes(_urlopen_bytes(MANIFEST_PARQUET_URL, timeout=120))
    except (urllib.error.URLError, OSError) as exc:
        print(f"  no parquet base available ({exc})")
        return None
    print(f"  fetched {LOCAL_BASE_PARQUET.stat().st_size:,} bytes")
    return LOCAL_BASE_PARQUET


def fetch_ia_file_names() -> list[str]:
    """List all file names in the dashboard item via the metadata API."""
    try:
        payload = json.loads(_urlopen_bytes(IA_FILES_METADATA_URL, timeout=30).decode())
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"  warning: could not fetch IA file listing: {exc}")
        return []
    return [f.get("name", "") for f in payload.get("result", []) if isinstance(f, dict)]


def fetch_delta_urls(names: list[str]) -> list[str]:
    """Legacy top-level upload-deltas-*.csv files (5-col, no djen_raw)."""
    return [
        f"{IA_DOWNLOAD_BASE}/{n}"
        for n in sorted(names)
        if n.startswith("upload-deltas-") and n.endswith(".csv") and "/" not in n
    ]


def fetch_segment_names(names: list[str]) -> list[str]:
    """Un-compacted manifest-log/ segments (6-col upsert events)."""
    return sorted(
        n
        for n in names
        if n.startswith(f"{SEGMENT_DIR}/")
        and not n.startswith(f"{SEGMENT_COMPACTED_DIR}/")
        and n.endswith(".csv")
    )


def download_segments(names: list[str]) -> list[tuple[str, Path]]:
    """Download segments locally. Returns (remote_name, local_path) pairs.

    Only successfully downloaded segments are merged — and only merged
    segments are pruned afterwards, so a failed download simply leaves the
    segment for the next compaction run.

    Each segment gets a short, bounded retry (_RETRY_IA_SEGMENT). After
    SEGMENT_CIRCUIT_BREAKER_THRESHOLD consecutive failures, the rest of the
    batch is skipped outright rather than attempted one by one — see the
    comment above _RETRY_IA_SEGMENT for why.
    """
    LOCAL_SEGMENT_DIR.mkdir(parents=True, exist_ok=True)
    out: list[tuple[str, Path]] = []
    consecutive_failures = 0
    for i, name in enumerate(names):
        if consecutive_failures >= SEGMENT_CIRCUIT_BREAKER_THRESHOLD:
            print(
                f"  {consecutive_failures} consecutive segment failures — IA looks "
                f"unavailable, skipping remaining {len(names) - i} segment(s) for next run"
            )
            break
        local = LOCAL_SEGMENT_DIR / name.split("/")[-1]
        try:
            local.write_bytes(_urlopen_bytes_segment(f"{IA_DOWNLOAD_BASE}/{name}", timeout=60))
        except (urllib.error.URLError, OSError) as exc:
            print(f"  warning: could not download segment {name}: {exc}")
            consecutive_failures += 1
            continue
        consecutive_failures = 0
        out.append((name, local))
    return out


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------


def _load_base(con: duckdb.DuckDBPyConnection, base_parquet: Path | None) -> str:
    """Create the ``manifest`` table from the parquet base.

    Phase 3: there is no CSV fallback. If the parquet base is unavailable,
    compaction cannot proceed.
    """
    if base_parquet is None:
        msg = "parquet base indisponível — sem fallback CSV na Fase 3"
        raise RuntimeError(msg)
    con.execute(
        f"""
        CREATE TABLE manifest AS
        SELECT tribunal::VARCHAR AS tribunal, date::DATE AS date,
               ia_status::VARCHAR AS ia_status, djen_status::VARCHAR AS djen_status,
               djen_raw::VARCHAR AS djen_raw, updated_at::VARCHAR AS updated_at
        FROM read_parquet('{base_parquet}')
        """
    )
    return "parquet"


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


def _apply_segments(
    con: duckdb.DuckDBPyConnection, segment_paths: list[str]
) -> tuple[int, int, int]:
    """Merge manifest-log/ segments (6-col upsert events) into ``manifest``.

    Field-by-field, last-write-wins by ``updated_at`` (plan §4.1): empty
    fields mean "no change"; ``ia_status='uploaded'`` is monotonic (a
    verified archive fact is never reverted); DJEN fields (status + raw as a
    coherent pair from the same event) apply when the event is not older
    than the row. Keys unknown to the base are inserted.
    Returns (uploaded, djen, inserted) counts.
    """
    con.execute(
        """
        CREATE TABLE segments (
            tribunal VARCHAR, date DATE, ia_status VARCHAR,
            djen_status VARCHAR, djen_raw VARCHAR, updated_at VARCHAR
        )
        """
    )
    for path in segment_paths:
        try:
            con.execute(
                f"""
                INSERT INTO segments
                SELECT tribunal::VARCHAR, date::DATE, ia_status::VARCHAR,
                       djen_status::VARCHAR, djen_raw::VARCHAR, updated_at::VARCHAR
                FROM read_csv_auto('{path}', header=true, types={_CSV_TYPES})
                """
            )
        except (duckdb.Error, OSError) as exc:
            print(f"  warning: could not read segment {path}: {exc}")

    seg_uploaded = con.execute(
        """
        UPDATE manifest
        SET ia_status = 'uploaded',
            updated_at = greatest(coalesce(manifest.updated_at, ''), s.updated_at)
        FROM (
            SELECT tribunal, date, max(coalesce(updated_at, '')) AS updated_at
            FROM segments WHERE ia_status = 'uploaded' GROUP BY tribunal, date
        ) s
        WHERE manifest.tribunal = s.tribunal AND manifest.date = s.date
          AND (manifest.ia_status IS NULL OR manifest.ia_status != 'uploaded')
        """
    ).fetchone()[0]

    seg_djen = con.execute(
        """
        UPDATE manifest
        SET djen_status = nullif(s.djen_status, ''),
            djen_raw = nullif(s.djen_raw, ''),
            updated_at = greatest(coalesce(manifest.updated_at, ''), s.updated_at)
        FROM (
            SELECT tribunal, date, djen_status, djen_raw, updated_at FROM (
                SELECT *, row_number() OVER (
                    PARTITION BY tribunal, date ORDER BY coalesce(updated_at, '') DESC
                ) AS rn
                FROM segments
                WHERE coalesce(djen_status, '') != '' OR coalesce(djen_raw, '') != ''
            ) WHERE rn = 1
        ) s
        WHERE manifest.tribunal = s.tribunal AND manifest.date = s.date
          AND coalesce(s.updated_at, '') >= coalesce(manifest.updated_at, '')
        """
    ).fetchone()[0]

    seg_inserted = con.execute(
        """
        INSERT INTO manifest
        SELECT s.tribunal, s.date, nullif(s.ia_status, ''), nullif(s.djen_status, ''),
               nullif(s.djen_raw, ''), s.updated_at
        FROM (
            SELECT * FROM (
                SELECT *, row_number() OVER (
                    PARTITION BY tribunal, date ORDER BY coalesce(updated_at, '') DESC
                ) AS rn
                FROM segments
            ) WHERE rn = 1
        ) s
        LEFT JOIN manifest m ON m.tribunal = s.tribunal AND m.date = s.date
        WHERE m.tribunal IS NULL
        """
    ).fetchone()[0]

    if segment_paths:
        print(
            f"  merged {seg_uploaded} uploaded + {seg_djen} djen rows "
            f"(+{seg_inserted} inserted) from {len(segment_paths)} segment(s)"
        )
    return seg_uploaded, seg_djen, seg_inserted


def _normalize_manifest(con: duckdb.DuckDBPyConnection) -> None:
    """Make absent rows self-consistent (plan §5, Fase 1).

    ``djen_status='absent'`` with a bare 200 raw contradicts itself —
    ``interpret_djen_raw('200')`` would re-derive ``available``. Rewrite the
    raw to the ``no_publications`` sentinel so the verdict is reproducible
    from the raw alone, regardless of which consumer reads it.
    """
    fixed = con.execute(
        """
        UPDATE manifest SET djen_raw = 'no_publications'
        WHERE djen_status = 'absent'
          AND (djen_raw = '200' OR djen_raw LIKE '200:%')
        """
    ).fetchone()[0]
    if fixed:
        print(f"  normalized {fixed} absent rows with a contradictory 200 raw")


def render_parquet(
    base_parquet: Path | None,
    delta_urls: list[str],
    segment_paths: list[str],
    *,
    write_back: bool = False,
) -> Path:
    """Compact base + deltas + segments into a new local parquet."""
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")

    base_kind = _load_base(con, base_parquet)
    print(f"  base: {base_kind}")

    _apply_deltas(con, delta_urls)
    _apply_segments(con, segment_paths)
    _normalize_manifest(con)

    con.execute(f"COPY manifest TO '{LOCAL_PARQUET}' (FORMAT PARQUET, COMPRESSION ZSTD)")

    _print_merge_stats(con)
    if write_back:
        write_back_csv(con)
    return LOCAL_PARQUET


def _print_merge_stats(con: duckdb.DuckDBPyConnection) -> None:
    """Show how the merge reshaped the manifest."""
    total = con.execute("SELECT count(*) FROM manifest").fetchone()[0]
    pending = con.execute(
        """SELECT count(*) FROM manifest
           WHERE djen_status IN ('available', 'confirmed')
             AND (ia_status IS NULL OR ia_status != 'uploaded')"""
    ).fetchone()[0]
    print(f"  merged manifest: {total:,} rows")
    print(f"  pending uploads after merge: {pending:,}")


def write_back_csv(con: duckdb.DuckDBPyConnection) -> Path:
    """Export the merged manifest to the legacy CSV layout.

    Phase 2: the CSV is now a *derived export* for consumers that still read
    it (plan §5 Fase 3 makes it fully optional). The new-format engine never
    rewrites the canonical CSV, so keeping this fresh is race-free once the
    Phase 2 engine is deployed.

    Self-consistency: rows the merge reclassified to ``absent`` while the raw
    stayed ``200`` are rewritten to the ``no_publications`` sentinel (also
    done in the parquet itself by ``_normalize_manifest``).

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


# ---------------------------------------------------------------------------
# Upload + prune
# ---------------------------------------------------------------------------


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _get_ia_auth() -> str | None:
    if os.environ.get("IAS3_ACCESS_KEY") and os.environ.get("IAS3_SECRET_KEY"):
        return f"LOW {os.environ['IAS3_ACCESS_KEY']}:{os.environ['IAS3_SECRET_KEY']}"
    return None


async def upload(path: Path, target: str) -> bool:
    auth = _get_ia_auth()
    if not auth:
        print(f"No IA credentials — skipping upload of {target}")
        return False

    async with create_upload_client(auth) as client:
        ok = await upload_to_ia(client, IA_ITEM, path, target)
        print(f"{target}: {'uploaded' if ok else 'upload failed'}")
        return ok


async def prune_segments(absorbed: list[tuple[str, Path]]) -> int:
    """Move absorbed segments to manifest-log/compacted/ on IA (plan §4.3).

    Runs only AFTER the new parquet base was uploaded successfully. Copy to
    ``manifest-log/compacted/<name>`` first, delete the original second —
    a failure at any point leaves the segment in place, and re-absorbing it
    next run is idempotent (upserts). Archived copies are kept for
    audit/replay rather than deleted.
    """
    auth = _get_ia_auth()
    if not auth:
        print("No IA credentials — skipping segment prune")
        return 0

    pruned = 0
    headers = {
        "Content-Type": "text/csv",
        "x-amz-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
    }
    async with create_upload_client(auth) as client:
        for name, local in absorbed:
            basename = name.split("/")[-1]
            try:
                resp = await client.put(
                    f"{IA_S3_ITEM_URL}/{SEGMENT_COMPACTED_DIR}/{basename}",
                    content=local.read_bytes(),
                    headers=headers,
                )
                if resp.status_code >= 400:
                    print(f"  prune: archive copy failed for {name} ({resp.status_code})")
                    continue
                resp = await client.delete(f"{IA_S3_ITEM_URL}/{name}")
                if resp.status_code >= 400:
                    print(f"  prune: delete failed for {name} ({resp.status_code})")
                    continue
                pruned += 1
            except (httpx.HTTPError, httpx.RequestError, OSError) as exc:
                print(f"  prune: error for {name}: {exc}")
    print(f"  pruned {pruned}/{len(absorbed)} absorbed segment(s) → {SEGMENT_COMPACTED_DIR}/")
    return pruned


def main() -> None:
    # MANIFEST_COMPACT_WRITEBACK: also export + upload the merged state as the
    # legacy CSV (derived read replica for consumers not yet on the parquet).
    # MANIFEST_DRY_RUN renders + reports locally without touching IA.
    write_back = _env_truthy("MANIFEST_COMPACT_WRITEBACK")
    dry_run = _env_truthy("MANIFEST_DRY_RUN")

    base_parquet = ensure_base_parquet()

    names = fetch_ia_file_names()
    delta_urls = fetch_delta_urls(names)
    segment_names = fetch_segment_names(names)
    print(f"Delta files found: {len(delta_urls)}")
    print(f"Segments found: {len(segment_names)}")
    absorbed = download_segments(segment_names)

    parquet = render_parquet(
        base_parquet,
        delta_urls,
        [str(p) for _, p in absorbed],
        write_back=write_back,
    )
    uploaded_count = duckdb.execute(
        f"SELECT count(*) FROM read_parquet('{parquet}') WHERE ia_status = 'uploaded'"
    ).fetchone()[0]
    print(f"Parquet: {parquet} ({parquet.stat().st_size:,} bytes)")
    print(f"  ia_status=uploaded in parquet: {uploaded_count}")
    print(
        f"  write-back: {'ON' if write_back else 'off'}  |  dry-run: {'ON' if dry_run else 'off'}"
    )

    if dry_run:
        print("Dry run — no IA uploads, no pruning.")
        return

    base_uploaded = asyncio.run(upload(parquet, IA_TARGET))
    # Prune ONLY when the new base (which contains the absorbed segments) is
    # safely on IA — otherwise segments stay and are re-absorbed next run.
    if base_uploaded and absorbed:
        asyncio.run(prune_segments(absorbed))
    if write_back:
        asyncio.run(upload(LOCAL_CSV, "sync-manifest.csv"))


if __name__ == "__main__":
    main()
