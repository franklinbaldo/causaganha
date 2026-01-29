#!/usr/bin/env python3
"""Generate dashboard cache JSON files from the catalog manifest.

Reads manifest.parquet (the catalog's index of all IA files) and derives
all dashboard data from it, instead of making per-date IA API calls.

Data sources:
  - manifest.parquet from causaganha-catalog (one HTTP fetch via DuckDB httpfs)
  - IA search API for item sizes (one HTTP call)
  - GitHub API for workflow runs (one HTTP call)

Usage:
  python generate_dashboard_cache.py                     # Generate local cache
  python generate_dashboard_cache.py --manifest ./m.parquet  # Use local manifest

Outputs:
  - dashboard/public/cache/meta.json     # Version and timestamp
  - dashboard/public/cache/today.json    # Today's metrics and tribunal status
  - dashboard/public/cache/runs.json     # Recent GitHub Actions runs
  - dashboard/public/cache/calendar.json # Historical calendar data
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb


# Configuration
CALENDAR_DAYS = 120
GITHUB_REPO = "franklinbaldo/causaganha"
OUTPUT_DIR = Path(__file__).parent.parent / "dashboard" / "public" / "cache"
MANIFEST_URL = "https://archive.org/download/causaganha-catalog/manifest.parquet"
IA_SEARCH_URL = (
    "https://archive.org/advancedsearch.php"
    "?q=identifier:djen-20*"
    "&fl[]=identifier&fl[]=item_size"
    "&rows=10000&output=json"
)

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


def fetch_json(url: str, timeout: int = 30) -> dict[str, Any] | None:
    """Fetch JSON from URL with error handling."""
    try:
        req = urllib.request.Request(  # noqa: S310
            url,
            headers={"User-Agent": "CausaGanha-Dashboard/3.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310
            data: dict[str, Any] = json.loads(response.read().decode())
            return data
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  Warning: Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def load_manifest(con: duckdb.DuckDBPyConnection, manifest_path: str | None) -> bool:
    """Load manifest.parquet into DuckDB, from local path or remote URL."""
    source = manifest_path or MANIFEST_URL

    if manifest_path:
        print(f"  Loading manifest from local file: {source}")
    else:
        print(f"  Loading manifest from IA: {source}")

    try:
        con.execute(f"""
            CREATE TABLE manifest AS
            SELECT * FROM read_parquet('{source}')
        """)

        # Check if manifest has expected schema
        schema = [col[0] for col in con.execute("DESCRIBE manifest").fetchall()]
        if "date" not in schema:
            print("  Warning: Manifest has no 'date' column - creating empty fallback table")
            con.execute("DROP TABLE manifest")
            con.execute("""
                CREATE TABLE manifest (
                    date VARCHAR,
                    tribunal VARCHAR,
                    file_type VARCHAR,
                    table_name VARCHAR,
                    file_name VARCHAR,
                    ia_item VARCHAR,
                    ia_url VARCHAR,
                    created_at VARCHAR
                )
            """)
            print("  Created empty manifest with proper schema")
            return True

        count = con.execute("SELECT COUNT(*) FROM manifest").fetchone()
        print(f"  Loaded {count[0]} manifest entries")
        return True
    except Exception as e:
        print(f"  Error loading manifest: {e}", file=sys.stderr)
        # Create empty fallback table
        print("  Creating empty fallback manifest table...")
        try:
            con.execute("""
                CREATE TABLE manifest (
                    date VARCHAR,
                    tribunal VARCHAR,
                    file_type VARCHAR,
                    table_name VARCHAR,
                    file_name VARCHAR,
                    ia_item VARCHAR,
                    ia_url VARCHAR,
                    created_at VARCHAR
                )
            """)
            return True
        except Exception:
            return False


def fetch_item_sizes() -> dict[str, int]:
    """Fetch item sizes from IA search API (one bulk request)."""
    print("  Fetching item sizes from IA search API...")
    data = fetch_json(IA_SEARCH_URL)
    if not data or "response" not in data:
        print("  Warning: Could not fetch item sizes", file=sys.stderr)
        return {}

    sizes: dict[str, int] = {}
    for doc in data["response"].get("docs", []):
        identifier = doc.get("identifier", "")
        item_size = doc.get("item_size", 0)
        # Extract date from identifier: djen-YYYY-MM-DD -> YYYY-MM-DD
        if identifier.startswith("djen-") and len(identifier) >= 15:
            date_str = identifier[5:15]  # "YYYY-MM-DD"
            sizes[date_str] = int(item_size) if item_size else 0

    print(f"  Got sizes for {len(sizes)} dates")
    return sizes


def generate_today_cache(con: duckdb.DuckDBPyConnection, sizes: dict[str, int]) -> dict[str, Any]:
    """Generate today's metrics and tribunal status from manifest."""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"  Generating today's data ({today})...")

    # Query manifest for today's tribunal statuses
    result = con.execute(
        """
        SELECT tribunal, file_type
        FROM manifest
        WHERE date = ? AND file_type IN ('zip', 'absent')
    """,
        [today],
    ).fetchall()

    date_used = today
    if not result:
        print(f"  No data for today, trying yesterday ({yesterday})...")
        result = con.execute(
            """
            SELECT tribunal, file_type
            FROM manifest
            WHERE date = ? AND file_type IN ('zip', 'absent')
        """,
            [yesterday],
        ).fetchall()
        date_used = yesterday

    # Build tribunal status map
    tribunal_status: dict[str, dict[str, Any]] = {}
    for tribunal, file_type in result:
        tribunal_status[tribunal] = {
            "status": "ok" if file_type == "zip" else "absent",
            "size": None,  # Per-tribunal sizes not in manifest
        }

    # Mark missing tribunals as pending
    for tribunal in TRIBUNALS:
        if tribunal not in tribunal_status:
            tribunal_status[tribunal] = {"status": "pending", "size": None}

    # Calculate metrics
    zip_count = sum(1 for t in tribunal_status.values() if t["status"] == "ok")
    size_today = sizes.get(date_used, 0)

    return {
        "date": date_used,
        "files_today": zip_count,
        "size_today": size_today,
        "tribunal_status": tribunal_status,
    }


def generate_runs_cache() -> dict[str, Any]:
    """Fetch recent GitHub Actions runs."""
    print("  Fetching GitHub Actions runs...")

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


def generate_calendar_cache(
    con: duckdb.DuckDBPyConnection,
    sizes: dict[str, int],
) -> dict[str, Any]:
    """Generate calendar data for last N days from manifest."""
    print(f"  Generating calendar data ({CALENDAR_DAYS} days)...")

    # Query manifest for zip counts per date
    result = con.execute(
        """
        SELECT date, COUNT(DISTINCT tribunal) as tribunal_count
        FROM manifest
        WHERE file_type = 'zip'
          AND date >= ?
        GROUP BY date
    """,
        [(datetime.now() - timedelta(days=CALENDAR_DAYS)).strftime("%Y-%m-%d")],
    ).fetchall()

    date_tribunals: dict[str, int] = {row[0]: row[1] for row in result}

    # Build calendar data
    calendar_data: dict[str, dict[str, Any]] = {}
    max_size = 0

    for i in range(CALENDAR_DAYS):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        size = sizes.get(date, 0)
        tribunal_count = date_tribunals.get(date, 0)
        exists = tribunal_count > 0 or size > 0

        calendar_data[date] = {
            "size": size,
            "tribunal_count": tribunal_count,
            "exists": exists,
        }
        max_size = max(max_size, size)

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

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>CausaGanha - DJEN Pipeline Status</title>
  <link>https://franklinbaldo.github.io/causaganha/</link>
  <description>Status updates from the CausaGanha judicial data collection pipeline</description>
  <language>pt-BR</language>
  <lastBuildDate>{now.strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>

  <item>
    <title>{date_str}: {files_today} tribunais, {format_bytes(size_today)}</title>
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


def main() -> None:
    """Generate all cache files from catalog manifest."""
    parser = argparse.ArgumentParser(description="Generate dashboard cache from catalog manifest")
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="Path to local manifest.parquet (default: download from IA)",
    )
    args = parser.parse_args()

    print("Generating dashboard cache from catalog manifest...")
    print(f"   Output: {OUTPUT_DIR}\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize DuckDB with httpfs for remote parquet access
    con = duckdb.connect()
    if not args.manifest:
        con.execute("INSTALL httpfs; LOAD httpfs;")

    # Step 1: Load manifest (one HTTP request or local file)
    print("[1/3] Loading manifest...")
    if not load_manifest(con, args.manifest):
        print("Error: Could not load manifest. Aborting.", file=sys.stderr)
        sys.exit(1)

    # Step 2: Fetch item sizes from IA search API (one HTTP request)
    print("[2/3] Fetching item sizes...")
    sizes = fetch_item_sizes()

    # Step 3: Generate all caches
    print("[3/3] Generating cache files...")
    today_data = generate_today_cache(con, sizes)
    runs_data = generate_runs_cache()
    calendar_data = generate_calendar_cache(con, sizes)

    con.close()

    # Add days_archived and health to today data
    today_data["days_archived"] = calendar_data["stats"]["days_with_data"]
    today_data["health"] = runs_data["health"]

    # Generate metadata
    meta = {
        "version": "3.0",
        "generated_at": datetime.now().isoformat() + "Z",
        "source": "manifest.parquet",
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
            json.dump(data, f, separators=(",", ":"))
        size = path.stat().st_size
        print(f"  {filename}: {size:,} bytes")

    # Generate RSS feed
    rss_content = generate_rss_feed(today_data, runs_data, calendar_data)
    rss_path = OUTPUT_DIR / "feed.xml"
    with rss_path.open("w") as f:
        f.write(rss_content)
    print(f"  feed.xml: {rss_path.stat().st_size:,} bytes")

    print("\nCache generation complete!")
    print(f"  Data source: manifest.parquet ({calendar_data['stats']['days_with_data']} days)")
    print("  HTTP requests: 3 (manifest + IA sizes + GH runs)")


if __name__ == "__main__":
    main()
