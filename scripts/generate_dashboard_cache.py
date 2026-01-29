#!/usr/bin/env python3
"""Generate dashboard cache JSON files from IA and GitHub APIs.

Usage:
  python generate_dashboard_cache.py           # Generate local cache only
  python generate_dashboard_cache.py --upload  # Generate and upload to IA

Outputs (local):
  - public/cache/meta.json     # Version and timestamp
  - public/cache/today.json    # Today's metrics and tribunal status
  - public/cache/runs.json     # Recent GitHub Actions runs
  - public/cache/calendar.json # Historical calendar data (120 days)

Outputs (IA):
  - https://archive.org/download/djen-dashboard-cache/cache.json
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


# Configuration
CALENDAR_DAYS = 120
GITHUB_REPO = "franklinbaldo/causaganha"
OUTPUT_DIR = Path(__file__).parent.parent / "dashboard" / "public" / "cache"

TRIBUNALS = [
    "STF",
    "STJ",
    "TST",
    "TSE",
    "STM",
    "CNJ",
    "TRF1",
    "TRF2",
    "TRF3",
    "TRF4",
    "TRF5",
    "TRF6",
    "TRT1",
    "TRT2",
    "TRT3",
    "TRT4",
    "TRT5",
    "TRT6",
    "TRT7",
    "TRT8",
    "TRT9",
    "TRT10",
    "TRT11",
    "TRT12",
    "TRT13",
    "TRT14",
    "TRT15",
    "TRT16",
    "TRT17",
    "TRT18",
    "TRT19",
    "TRT20",
    "TRT21",
    "TRT22",
    "TRT23",
    "TRT24",
    "TJAC",
    "TJAL",
    "TJAM",
    "TJAP",
    "TJBA",
    "TJCE",
    "TJDFT",
    "TJES",
    "TJGO",
    "TJMA",
    "TJMG",
    "TJMS",
    "TJMT",
    "TJPA",
    "TJPB",
    "TJPE",
    "TJPI",
    "TJPR",
    "TJRJ",
    "TJRN",
    "TJRO",
    "TJRR",
    "TJRS",
    "TJSC",
    "TJSE",
    "TJSP",
    "TJTO",
]


def fetch_json(url: str, timeout: int = 10) -> dict[str, Any] | None:
    """Fetch JSON from URL with error handling."""
    try:
        req = urllib.request.Request(  # noqa: S310
            url,
            headers={"User-Agent": "CausaGanha-Dashboard/2.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310
            data: dict[str, Any] = json.loads(response.read().decode())
            return data
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  ⚠ Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def fetch_ia_metadata(date: str) -> dict[str, Any] | None:
    """Fetch Internet Archive metadata for a specific date."""
    url = f"https://archive.org/metadata/djen-{date}"
    return fetch_json(url)


def parse_tribunal_status(metadata: dict[str, Any] | None, date: str) -> dict[str, dict[str, Any]]:
    """Parse IA metadata into tribunal status dict."""
    if not metadata or "files" not in metadata:
        return {}

    status: dict[str, dict[str, Any]] = {}
    for file in metadata.get("files", []):
        name = file.get("name", "")
        # Match pattern: djen-YYYY-MM-DD-TRIBUNAL.zip or .absent
        if name.startswith(f"djen-{date}-") and name.endswith((".zip", ".absent")):
            parts = name.replace(f"djen-{date}-", "").rsplit(".", 1)
            if len(parts) == 2:
                tribunal = parts[0]
                ext = parts[1]
                status[tribunal] = {
                    "status": "ok" if ext == "zip" else "absent",
                    "size": int(file.get("size", 0)) if ext == "zip" else None,
                }
    return status


def generate_today_cache() -> dict[str, Any]:
    """Generate today's metrics and tribunal status."""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"📊 Fetching today's data ({today})...")

    # Try today, fall back to yesterday
    metadata = fetch_ia_metadata(today)
    date_used = today

    if not metadata or not metadata.get("files"):
        print(f"  → No data for today, trying yesterday ({yesterday})...")
        metadata = fetch_ia_metadata(yesterday)
        date_used = yesterday

    tribunal_status = parse_tribunal_status(metadata, date_used)

    # Calculate metrics
    zip_files = [t for t in tribunal_status.values() if t["status"] == "ok"]
    files_today = len(zip_files)
    size_today = sum(t.get("size", 0) or 0 for t in zip_files)

    # Mark missing tribunals as pending
    for tribunal in TRIBUNALS:
        if tribunal not in tribunal_status:
            tribunal_status[tribunal] = {"status": "pending", "size": None}

    return {
        "date": date_used,
        "files_today": files_today,
        "size_today": size_today,
        "tribunal_status": tribunal_status,
    }


def generate_runs_cache() -> dict[str, Any]:
    """Fetch recent GitHub Actions runs."""
    print("🔄 Fetching GitHub Actions runs...")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs?per_page=10"
    data = fetch_json(url)

    if not data or "workflow_runs" not in data:
        return {"runs": [], "health": 0}

    runs = []
    for run in data.get("workflow_runs", [])[:10]:
        runs.append(
            {
                "id": run.get("id"),
                "name": run.get("display_title") or run.get("name"),
                "run_number": run.get("run_number"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "created_at": run.get("created_at"),
                "html_url": run.get("html_url"),
            },
        )

    # Calculate health percentage
    completed = [r for r in runs if r["conclusion"]]
    successful = [r for r in completed if r["conclusion"] == "success"]
    health = round((len(successful) / len(completed)) * 100) if completed else 0

    return {"runs": runs, "health": health}


def generate_calendar_cache(existing_calendar: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate calendar data for last N days (incremental update)."""
    print(f"📅 Generating calendar data ({CALENDAR_DAYS} days)...")

    existing_data = existing_calendar.get("days", {}) if existing_calendar else {}
    calendar_data: dict[str, dict[str, Any]] = {}
    max_size = 0

    for i in range(CALENDAR_DAYS):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")

        # Skip if we already have this historical date (not today/yesterday)
        if date in existing_data and i > 1:
            calendar_data[date] = existing_data[date]
            max_size = max(max_size, existing_data[date].get("size", 0))
            continue

        metadata = fetch_ia_metadata(date)

        if metadata and metadata.get("files"):
            zip_files = [f for f in metadata["files"] if f.get("name", "").endswith(".zip")]
            size = metadata.get("item_size", 0) or 0
            tribunal_count = len(zip_files)
            calendar_data[date] = {
                "size": size,
                "tribunal_count": tribunal_count,
                "exists": True,
            }
            max_size = max(max_size, size)
        else:
            calendar_data[date] = {"size": 0, "tribunal_count": 0, "exists": False}

        # Rate limit
        if i % 10 == 9:
            print(f"  → Processed {i + 1}/{CALENDAR_DAYS} days...")

    # Calculate levels based on max size
    for data in calendar_data.values():
        if max_size > 0 and data["size"] > 0:
            ratio = data["size"] / max_size
            if ratio >= 0.76:
                data["level"] = 4
            elif ratio >= 0.51:
                data["level"] = 3
            elif ratio >= 0.26:
                data["level"] = 2
            else:
                data["level"] = 1
        else:
            data["level"] = 0

    # Calculate summary stats
    days_with_data = [d for d in calendar_data.values() if d["exists"]]
    total_size = sum(d["size"] for d in days_with_data)
    biggest_day = max(
        calendar_data.items(),
        key=lambda x: x[1]["size"],
        default=(None, {"size": 0}),
    )

    return {
        "days": calendar_data,
        "stats": {
            "total_size": total_size,
            "days_with_data": len(days_with_data),
            "biggest_day": biggest_day[0] if biggest_day[1]["size"] > 0 else None,
            "biggest_size": biggest_day[1]["size"],
        },
    }


def format_bytes(size: float) -> str:
    """Format bytes to human readable string."""
    size_f = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_f < 1024:
            return f"{size_f:.1f} {unit}"
        size_f /= 1024
    return f"{size_f:.1f} TB"


def generate_rss_feed(
    today_data: dict[str, Any],
    runs_data: dict[str, Any],
    calendar_data: dict[str, Any],
) -> str:
    """Generate RSS feed with status updates."""
    now = datetime.now()
    date_str = today_data.get("date", now.strftime("%Y-%m-%d"))
    files_today = today_data.get("files_today", 0)
    size_today = today_data.get("size_today", 0)
    health = today_data.get("health", 0)

    # Build RSS
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>CausaGanha - DJEN Pipeline Status</title>
  <link>https://franklinbaldo.github.io/causaganha/</link>
  <description>Status updates from the CausaGanha judicial data collection pipeline</description>
  <language>pt-BR</language>
  <lastBuildDate>{now.strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
  <atom:link href="https://archive.org/download/djen-dashboard-cache/feed.xml" rel="self" type="application/rss+xml"/>

  <item>
    <title>📊 {date_str}: {files_today} tribunais, {format_bytes(size_today)}</title>
    <link>https://archive.org/details/djen-{date_str}</link>
    <description>
      Pipeline Status: {health}% healthy
      Tribunais coletados: {files_today}/91
      Volume: {format_bytes(size_today)}
      Dias arquivados: {calendar_data["stats"]["days_with_data"]}
    </description>
    <pubDate>{now.strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
    <guid isPermaLink="false">causaganha-{now.strftime("%Y%m%d%H%M%S")}</guid>
  </item>

</channel>
</rss>"""


def upload_to_ia(cache_data: dict[str, Any], rss_content: str) -> bool:
    """Upload cache.json and feed.xml to Internet Archive."""
    import tempfile

    try:
        from internetarchive import upload
    except ImportError:
        print("  ⚠ internetarchive library not installed. Run: pip install internetarchive")
        return False

    print("📤 Uploading to Internet Archive...")

    item_id = "djen-dashboard-cache"
    metadata = {
        "title": "CausaGanha Dashboard Cache",
        "description": "Auto-generated cache for the CausaGanha dashboard. Updated every pipeline run.",
        "creator": "CausaGanha",
        "mediatype": "data",
        "collection": "opensource_media",
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "cache.json"
        rss_path = Path(tmpdir) / "feed.xml"

        with cache_path.open("w") as f:
            json.dump(cache_data, f, separators=(",", ":"))

        with rss_path.open("w") as f:
            f.write(rss_content)

        try:
            upload(
                item_id,
                files=[str(cache_path), str(rss_path)],
                metadata=metadata,
                retries=3,
            )
            print(f"  ✓ Uploaded to https://archive.org/download/{item_id}/")
            return True
        except Exception as e:
            print(f"  ⚠ Upload failed: {e}")
            return False


def main() -> None:
    """Generate all cache files."""
    parser = argparse.ArgumentParser(description="Generate dashboard cache")
    parser.add_argument("--upload", action="store_true", help="Upload to Internet Archive")
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Skip calendar fetch, use existing",
    )
    args = parser.parse_args()

    print("🚀 Generating dashboard cache...")
    print(f"   Output: {OUTPUT_DIR}\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing calendar for incremental update
    calendar_path = OUTPUT_DIR / "calendar.json"
    existing_calendar = None
    if calendar_path.exists():
        try:
            with calendar_path.open() as f:
                existing_calendar = json.load(f)
        except json.JSONDecodeError:
            pass

    # Generate all caches
    today_data = generate_today_cache()
    runs_data = generate_runs_cache()

    if args.local_only and existing_calendar:
        print("📅 Using existing calendar data (--local-only)")
        calendar_data = existing_calendar
    else:
        calendar_data = generate_calendar_cache(existing_calendar)

    # Add days_archived to today data
    today_data["days_archived"] = calendar_data["stats"]["days_with_data"]
    today_data["health"] = runs_data["health"]

    # Generate metadata
    meta = {
        "version": "2.0",
        "generated_at": datetime.now().isoformat() + "Z",
        "calendar_days": CALENDAR_DAYS,
    }

    # Write local files
    files = {
        "meta.json": meta,
        "today.json": today_data,
        "runs.json": runs_data,
        "calendar.json": calendar_data,
    }

    for filename, data in files.items():
        path = OUTPUT_DIR / filename
        with path.open("w") as f:
            json.dump(data, f, separators=(",", ":"))  # Compact JSON
        size = path.stat().st_size
        print(f"  ✓ {filename}: {size:,} bytes")

    # Generate combined cache for IA
    combined_cache = {
        "meta": meta,
        "today": today_data,
        "runs": runs_data,
        "calendar": calendar_data,
    }

    # Generate RSS feed
    rss_content = generate_rss_feed(today_data, runs_data, calendar_data)
    rss_path = OUTPUT_DIR / "feed.xml"
    with rss_path.open("w") as f:
        f.write(rss_content)
    print(f"  ✓ feed.xml: {rss_path.stat().st_size:,} bytes")

    print("\n✅ Cache generation complete!")

    # Upload to IA if requested
    if args.upload:
        upload_to_ia(combined_cache, rss_content)
    else:
        print("   (Use --upload to push to Internet Archive)")


if __name__ == "__main__":
    main()
