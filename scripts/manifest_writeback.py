#!/usr/bin/env python3
"""Phase 1: Manifest write-back — correct ~79K false-available rows.

The legacy checker recorded HTTP 200 in djen_raw without inspecting the
response body. DJEN returns 200 with body {"status": "Sem comunicações"}
when there is no publication — so djen_raw='200' does NOT mean available.

This script corrects rows where:
  - djen_raw = '200'
  - djen_status = 'available'
  - ia_status != 'uploaded' (no ZIP was ever obtained — confirming it was
    a false positive; genuinely available entries would have been downloaded)

Correction: djen_raw → 'no_publications', djen_status → 'absent'.

Usage:
    python scripts/manifest_writeback.py [--dry-run] [--manifest PATH]
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import UTC, datetime
from pathlib import Path

import structlog


log = structlog.get_logger()

DEFAULT_MANIFEST = Path("data/sync-manifest.csv")
HEADER_FIELDS = ["tribunal", "date", "ia_status", "djen_status", "djen_raw", "updated_at"]


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def correct_false_availables(
    rows: list[dict[str, str]],
    *,
    dry_run: bool,
) -> tuple[list[dict[str, str]], int]:
    now = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    corrected = 0

    for row in rows:
        djen_raw = row.get("djen_raw", "")
        djen_status = row.get("djen_status", "")
        ia_status = row.get("ia_status", "")

        if djen_raw == "200" and djen_status == "available" and ia_status != "uploaded":
            if not dry_run:
                row["djen_raw"] = "no_publications"
                row["djen_status"] = "absent"
                row["updated_at"] = now
            corrected += 1

    return rows, corrected


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manifest write-back: correct false-available rows",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to sync-manifest.csv",
    )
    parser.add_argument("--dry-run", action="store_true", help="Count corrections without writing")
    args = parser.parse_args()

    manifest_path: Path = args.manifest
    if not manifest_path.exists():
        log.error("manifest_not_found", path=str(manifest_path))
        sys.exit(2)

    rows = load_manifest(manifest_path)
    log.info("manifest_loaded", total_rows=len(rows))

    total_200_available = sum(
        1 for r in rows if r.get("djen_raw") == "200" and r.get("djen_status") == "available"
    )
    uploaded_200 = sum(
        1
        for r in rows
        if r.get("djen_raw") == "200"
        and r.get("djen_status") == "available"
        and r.get("ia_status") == "uploaded"
    )
    log.info(
        "pre_correction_stats",
        total_200_available=total_200_available,
        uploaded_and_200=uploaded_200,
        false_available_candidates=total_200_available - uploaded_200,
    )

    rows, corrected = correct_false_availables(rows, dry_run=args.dry_run)

    if args.dry_run:
        log.info("dry_run_complete", would_correct=corrected)
        print(f"\nDRY RUN: {corrected} rows would be corrected")
        print(f"  Total djen_raw='200' + available: {total_200_available}")
        print(f"  Of which uploaded (genuine): {uploaded_200}")
        print(f"  False-available (to correct): {corrected}")
    else:
        write_manifest(manifest_path, rows)
        log.info("manifest_written", corrected=corrected, path=str(manifest_path))
        print(f"\nCORRECTED: {corrected} rows updated in {manifest_path}")

    print("\n--- Summary ---")
    print(f"Total rows: {len(rows)}")
    print(f"Corrected: {corrected}")

    post_available = sum(1 for r in rows if r.get("djen_status") == "available")
    post_absent = sum(1 for r in rows if r.get("djen_status") == "absent")
    post_uploaded = sum(1 for r in rows if r.get("ia_status") == "uploaded")
    print(f"Post-correction available: {post_available}")
    print(f"Post-correction absent: {post_absent}")
    print(f"Post-correction uploaded: {post_uploaded}")


if __name__ == "__main__":
    main()
