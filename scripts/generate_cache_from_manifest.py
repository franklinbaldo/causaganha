#!/usr/bin/env python3
"""Generate webapp cache JSONs from the sync-manifest.

Reads `manifest-summary.json` from IA (produced by djen-backup engine)
and generates the legacy cache files that the webapp still expects:
- cache/backfill.json
- cache/today.json
- cache/meta.json
- cache/calendar.json
- cache/runs.json (empty, replaced by GitHub API calls at runtime)
- ia-snapshot.json

Usage:
    uv run python scripts/generate_cache_from_manifest.py
    uv run python scripts/generate_cache_from_manifest.py --upload
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

import argparse
import json
import subprocess
import urllib.request
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any


IA_DASHBOARD_ITEM = "causaganha-dashboard"


MANIFEST_SUMMARY_URL = "https://archive.org/download/causaganha-dashboard/manifest-summary.json"
MANIFEST_CSV_URL = "https://archive.org/download/causaganha-dashboard/sync-manifest.csv"
OUTPUT_DIR = Path(__file__).parent.parent / "web" / "public"
CACHE_DIR = OUTPUT_DIR / "cache"


def fetch_summary() -> dict[str, Any]:
    """Download manifest-summary.json from IA."""
    print(f"Fetching {MANIFEST_SUMMARY_URL}...")
    with urllib.request.urlopen(MANIFEST_SUMMARY_URL, timeout=60) as resp:
        data: dict[str, Any] = json.load(resp)
    print(f"  {data['totals']['total']} total entries, {len(data['tribunals'])} tribunals")
    return data


def fetch_manifest_csv() -> list[dict[str, str]]:
    """Download full manifest CSV for date-level detail."""
    import csv
    from io import StringIO

    print(f"Fetching {MANIFEST_CSV_URL}...")
    with urllib.request.urlopen(MANIFEST_CSV_URL, timeout=120) as resp:
        text = resp.read().decode("utf-8")
    rows = list(csv.DictReader(StringIO(text)))
    print(f"  {len(rows)} rows")
    return rows


def generate_backfill_json(summary: dict[str, Any], rows: list[dict[str, str]]) -> dict[str, Any]:
    """Generate cache/backfill.json in the format the webapp expects."""
    totals = summary["totals"]

    # Per-year progress
    progress_by_year: dict[str, dict[str, Any]] = {}
    for year_entry in summary["years"]:
        year = str(year_entry["year"])
        completed = year_entry["uploaded"]
        total = year_entry["total"]
        progress_by_year[year] = {
            "completed": completed,
            "total": total,
            "pct": round(completed / total * 100, 1) if total else 0,
            "absent": year_entry["absent"],
            "unknown": year_entry["unknown"],
        }

    # Daily stats for velocity calc — group uploaded entries by date
    by_date: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.get("ia_status") == "uploaded":
            by_date[row["date"]] += 1
    daily_stats = [{"date": d, "count": c} for d, c in sorted(by_date.items())]

    recent_activity = daily_stats[-30:] if daily_stats else []

    # tribunal coverage map
    tribunal_coverage = {t["tribunal"]: t["coverage_pct"] for t in summary["tribunals"]}

    # tribunal stats for grid
    tribunal_stats = [
        {
            "tribunal": t["tribunal"],
            "data_rate_pct": t["coverage_pct"],
            "uploaded": t["uploaded"],
            "total": t["total"],
            "earliest": t["earliest_upload"],
            "latest": t["latest_upload"],
        }
        for t in summary["tribunals"]
    ]

    # Archive snapshot (structured for homepage)
    archive_snapshot: dict[str, Any] = {
        "generated_at": summary["generated_at"],
        "items": {},
        "summary": {
            "total_zips": totals["uploaded"],
            "tribunals_total": len(summary["tribunals"]),
            "tribunals_with_data": sum(1 for t in summary["tribunals"] if t["uploaded"] > 0),
            "total_size_gb": 0,  # not tracked in summary
        },
    }

    # Populate items from tribunal summaries (grouped by tribunal+year)
    by_t_y: dict[tuple[str, int], list[str]] = defaultdict(list)
    for row in rows:
        if row.get("ia_status") == "uploaded":
            d = date.fromisoformat(row["date"])
            by_t_y[(row["tribunal"], d.year)].append(row["date"])
    for (tribunal, year), dates in sorted(by_t_y.items()):
        item_id = f"djen-{tribunal.lower()}-{year}"
        dates_sorted = sorted(dates)
        archive_snapshot["items"][item_id] = {
            "tribunal": tribunal,
            "year": year,
            "zip_count": len(dates_sorted),
            "total_size_bytes": 0,
            "dates": dates_sorted,
            "earliest_date": dates_sorted[0],
            "latest_date": dates_sorted[-1],
        }

    return {
        "progress_by_year": progress_by_year,
        "progress_pct": totals["coverage_pct"],
        "completed": totals["uploaded"],
        "backfill_done": totals["uploaded"],
        "total": totals["total"],
        "backfill_total": totals["total"],
        "backfill_progress": {
            "daily_stats": daily_stats,
            "recent_activity": recent_activity,
            "progress_pct": totals["coverage_pct"],
            "oldest_date": daily_stats[0]["date"] if daily_stats else "",
            "newest_date": daily_stats[-1]["date"] if daily_stats else "",
        },
        "tribunal_coverage": tribunal_coverage,
        "tribunal_absent_coverage": {
            t["tribunal"]: round(t["absent"] / t["total"] * 100, 1) if t["total"] else 0
            for t in summary["tribunals"]
        },
        "tribunal_stats": tribunal_stats,
        "archive_snapshot": archive_snapshot,
        "updated_at": summary["generated_at"],
    }


def generate_today_json(summary: dict[str, Any], rows: list[dict[str, str]]) -> dict[str, Any]:
    """Generate cache/today.json."""
    today = datetime.now(UTC).date()
    today_str = today.isoformat()

    files_today = sum(
        1 for r in rows if r.get("ia_status") == "uploaded" and r.get("date") == today_str
    )

    tribunal_status: dict[str, dict[str, Any]] = {}
    for t in summary["tribunals"]:
        if t["latest_upload"]:
            d = date.fromisoformat(t["latest_upload"])
            days_ago = (today - d).days
            status = "ok" if days_ago <= 2 else "pending" if days_ago <= 7 else "stale"
        else:
            status = "pending"
        tribunal_status[t["tribunal"]] = {
            "status": status,
            "last_update": t["latest_upload"] or "",
            "doc_count": t["uploaded"],
        }

    totals = summary["totals"]
    days_archived = len({r["date"] for r in rows if r.get("ia_status") == "uploaded"})

    return {
        "date": today_str,
        "files_today": files_today,
        "health": int(totals["coverage_pct"]),
        "days_archived": days_archived,
        "tribunal_status": tribunal_status,
        "pipeline": {
            "backfill_total": totals["total"],
            "backfill_done": totals["uploaded"],
            "progress_pct": totals["coverage_pct"],
            "days_consolidated": days_archived,
        },
    }


def generate_calendar_json(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Generate cache/calendar.json — daily coverage for heatmap."""
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=120)

    by_date: dict[str, dict[str, int]] = defaultdict(
        lambda: {"uploaded": 0, "absent": 0, "total": 0}
    )
    for row in rows:
        try:
            d = date.fromisoformat(row["date"])
        except (ValueError, KeyError):
            continue
        if d < cutoff:
            continue
        status = row.get("ia_status") or row.get("djen_status") or ""
        by_date[row["date"]]["total"] += 1
        if status == "uploaded":
            by_date[row["date"]]["uploaded"] += 1
        elif status == "absent":
            by_date[row["date"]]["absent"] += 1

    days = [
        {
            "date": d,
            "uploaded": v["uploaded"],
            "absent": v["absent"],
            "total": v["total"],
            "coverage_pct": round(v["uploaded"] / v["total"] * 100, 1) if v["total"] else 0,
        }
        for d, v in sorted(by_date.items())
    ]

    return {"days": days, "updated_at": datetime.now(UTC).isoformat()}


def generate_meta_json(summary: dict[str, Any]) -> dict[str, Any]:
    """Generate cache/meta.json — sentinel for change detection."""
    return {
        "version": 1,
        "generated_at": summary["generated_at"],
        "total_entries": summary["totals"]["total"],
        "uploaded": summary["totals"]["uploaded"],
    }


def generate_ia_snapshot(summary: dict[str, Any], rows: list[dict[str, str]]) -> dict[str, Any]:
    """Generate ia-snapshot.json at /public root (used by homepage)."""
    by_t_y: dict[tuple[str, int], list[str]] = defaultdict(list)
    for row in rows:
        if row.get("ia_status") == "uploaded":
            try:
                d = date.fromisoformat(row["date"])
            except ValueError:
                continue
            by_t_y[(row["tribunal"], d.year)].append(row["date"])

    items: dict[str, dict[str, Any]] = {}
    for (tribunal, year), dates in sorted(by_t_y.items()):
        item_id = f"djen-{tribunal.lower()}-{year}"
        ds = sorted(dates)
        items[item_id] = {
            "tribunal": tribunal,
            "year": year,
            "zip_count": len(ds),
            "total_size_bytes": 0,
            "dates": ds,
            "earliest_date": ds[0],
            "latest_date": ds[-1],
        }

    totals = summary["totals"]
    return {
        "generated_at": summary["generated_at"],
        "items": items,
        "summary": {
            "total_zips": totals["uploaded"],
            "tribunals_total": len(summary["tribunals"]),
            "tribunals_with_data": sum(1 for t in summary["tribunals"] if t["uploaded"] > 0),
            "total_size_gb": 0,
        },
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))
    print(f"  → {path.relative_to(OUTPUT_DIR.parent.parent)} ({path.stat().st_size:,} bytes)")


def upload_to_ia(paths: list[Path]) -> bool:
    """Upload generated JSONs to Internet Archive item causaganha-dashboard."""
    print(f"\nUploading {len(paths)} files to IA item {IA_DASHBOARD_ITEM}...")
    try:
        result = subprocess.run(
            [
                "ia",
                "upload",
                IA_DASHBOARD_ITEM,
                *[str(p) for p in paths],
                "--metadata=collection:opensource",
                "--metadata=mediatype:data",
                "--metadata=title:CausaGanha Dashboard Cache",
                "--metadata=description:Live cache JSONs for the CausaGanha dashboard.",
                "--metadata=subject:causaganha;dashboard;cache",
                "--metadata=creator:CausaGanha",
                "--retries=3",
                "--no-derive",
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("  Upload timed out")
        return False
    if result.returncode != 0:
        print(f"  Upload failed: {result.stderr}")
        return False
    print("  Upload complete")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upload",
        action="store_true",
        help=f"Upload generated JSONs to IA item {IA_DASHBOARD_ITEM}",
    )
    args = parser.parse_args()

    summary = fetch_summary()
    rows = fetch_manifest_csv()

    print("\nGenerating cache files...")
    written: list[Path] = []
    for rel, data in (
        (CACHE_DIR / "backfill.json", generate_backfill_json(summary, rows)),
        (CACHE_DIR / "today.json", generate_today_json(summary, rows)),
        (CACHE_DIR / "calendar.json", generate_calendar_json(rows)),
        (CACHE_DIR / "meta.json", generate_meta_json(summary)),
        (OUTPUT_DIR / "ia-snapshot.json", generate_ia_snapshot(summary, rows)),
        (CACHE_DIR / "runs.json", {"runs": [], "updated_at": summary["generated_at"]}),
    ):
        write_json(rel, data)
        written.append(rel)

    if args.upload and not upload_to_ia(written):
        raise SystemExit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
