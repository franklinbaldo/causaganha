#!/usr/bin/env python3
"""One-shot manifest reconciliation.

Three corrections applied to the canonical sync-manifest.csv:

1. **IA truth**: query metadata for every djen-{tribunal}-{year} item,
   mark those dates as ia_status='uploaded'.
2. **Reset legacy absents**: entries with djen_status='absent' but
   djen_raw='' (absent marked before we tracked raw codes). Re-check
   next run will re-classify them with a real raw code.
3. **Upload reconciled manifest** back to IA.

Usage::

    uv run --env-file ~/workspace/.env python scripts/reconcile_manifest.py

Requires IAS3_ACCESS_KEY + IAS3_SECRET_KEY for upload.
"""

from __future__ import annotations


# Safely reconfigure standard output and standard error encoding error handling on Windows
import sys
for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass

import asyncio
import os
import urllib.request
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from causaganha.pipeline.ia_s3 import create_upload_client, upload_to_ia
from djen_backup.archive import fetch_ia_existing
from djen_backup.manifest import SyncManifest


MANIFEST_URL = "https://archive.org/download/causaganha-dashboard/sync-manifest.csv"
LOCAL_CSV = Path("data/sync-manifest.csv")
IA_ITEM = "causaganha-dashboard"


def fetch_fresh_manifest() -> Path:
    LOCAL_CSV.parent.mkdir(parents=True, exist_ok=True)
    print(f"→ Downloading fresh manifest from {MANIFEST_URL}...")
    with urllib.request.urlopen(MANIFEST_URL, timeout=120) as resp:
        LOCAL_CSV.write_bytes(resp.read())
    print(f"  saved {LOCAL_CSV.stat().st_size:,} bytes")
    return LOCAL_CSV


def distribution(manifest: SyncManifest) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = defaultdict(int)
    for e in manifest._entries.values():
        out[(e.ia_status, e.djen_status)] += 1
    return out


def print_dist(label: str, dist: dict[tuple[str, str], int]) -> None:
    print(f"  {label}:")
    for (ia, djen), n in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"    {ia!r}|{djen!r}: {n:,}")


async def reconcile() -> None:
    csv_path = fetch_fresh_manifest()

    manifest = SyncManifest()
    manifest.load_from_disk(csv_path)
    total_before = len(manifest._entries)
    print(f"→ Loaded {total_before:,} entries")
    print_dist("before", distribution(manifest))

    # ── Step 1: IA truth ──────────────────────────────────────────
    # Query IA for every (tribunal, year) pair in the manifest so we can
    # trust the "not on IA" signal (needed to clear false ia_status=uploaded).
    pairs: set[tuple[str, int]] = {(e.tribunal, e.date.year) for e in manifest._entries.values()}
    print(f"\n→ Discovering IA state for {len(pairs)} (tribunal, year) pairs...")

    sem = asyncio.Semaphore(20)

    async def discover_one(
        client: httpx.AsyncClient, tribunal: str, year: int
    ) -> tuple[str, int, set[date], bool]:
        """Returns (tribunal, year, dates, queried_ok). queried_ok=False on error."""
        async with sem:
            try:
                ia_dates = await fetch_ia_existing(client, tribunal, year)
                return tribunal, year, set(ia_dates.keys()), True
            except (httpx.HTTPError, httpx.RequestError) as exc:
                print(f"  ! {tribunal}-{year}: {exc}")
                return tribunal, year, set(), False

    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    ia_dates_by_tribunal: dict[str, set[date]] = defaultdict(set)
    queried_ok: set[tuple[str, int]] = set()
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        results = await asyncio.gather(*(discover_one(client, t, y) for t, y in pairs))
    for tribunal, year, dates, ok in results:
        ia_dates_by_tribunal[tribunal].update(dates)
        if ok:
            queried_ok.add((tribunal, year))

    discovered = sum(len(v) for v in ia_dates_by_tribunal.values())
    print(
        f"  discovered {discovered:,} uploaded dates across {len(ia_dates_by_tribunal)} tribunals"
    )

    # Build IA truth set — only (tribunal, year) pairs we queried successfully.
    ia_truth: set[tuple[str, date]] = set()
    for tribunal, dates in ia_dates_by_tribunal.items():
        for d in dates:
            ia_truth.add((tribunal, d))

    # Rebuild from IA truth in both directions.
    now_ts = datetime.now(UTC).isoformat(timespec="seconds")
    added_uploaded = 0
    fixed_djen_status = 0
    cleared_false_uploaded = 0
    for key, entry in manifest._entries.items():
        on_ia = key in ia_truth
        pair_queried = (entry.tribunal, entry.date.year) in queried_ok

        if on_ia:
            if entry.ia_status != "uploaded":
                entry.ia_status = "uploaded"
                entry.updated_at = now_ts
                added_uploaded += 1
            # If on IA, DJEN must have had it → normalize djen_status
            if entry.djen_status != "available":
                entry.djen_status = "available"
                if not entry.djen_raw:
                    entry.djen_raw = "200"
                entry.updated_at = now_ts
                fixed_djen_status += 1
        elif entry.ia_status == "uploaded" and pair_queried:
            # Manifest claims uploaded but IA (successfully queried) doesn't have it → clear
            entry.ia_status = ""
            entry.updated_at = now_ts
            cleared_false_uploaded += 1

    print(f"→ Added ia_status=uploaded: {added_uploaded:,}")
    print(f"→ Normalized djen_status=available for uploaded: {fixed_djen_status:,}")
    print(f"→ Cleared false ia_status=uploaded (not on IA): {cleared_false_uploaded:,}")

    # ── Step 2: Reset legacy absents ──────────────────────────────
    legacy_reset = 0
    for entry in manifest._entries.values():
        if entry.djen_status == "absent" and not entry.djen_raw and entry.ia_status != "uploaded":
            entry.djen_status = ""
            legacy_reset += 1
    print(f"→ Reset {legacy_reset:,} legacy absents (no djen_raw)")

    # Invalidate caches before distribution + save
    manifest._counts_cache = None
    manifest._uploaded_items = None

    print_dist("after", distribution(manifest))

    # ── Step 3: Save + upload ─────────────────────────────────────
    manifest.save_to_disk(csv_path)
    print(f"\n→ Saved reconciled manifest to {csv_path} ({csv_path.stat().st_size:,} bytes)")

    auth = (
        f"LOW {os.environ['IAS3_ACCESS_KEY']}:{os.environ['IAS3_SECRET_KEY']}"
        if os.environ.get("IAS3_ACCESS_KEY") and os.environ.get("IAS3_SECRET_KEY")
        else None
    )
    if not auth:
        print("! No IA credentials — skipping upload")
        return

    print("→ Uploading to IA...")
    async with create_upload_client(auth) as client:
        ok = await upload_to_ia(client, IA_ITEM, csv_path, "sync-manifest.csv")
    print("  uploaded" if ok else "  upload failed")


if __name__ == "__main__":
    asyncio.run(reconcile())
