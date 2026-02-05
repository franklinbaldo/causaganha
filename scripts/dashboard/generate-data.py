#!/usr/bin/env python3
"""Generate dashboard-data.json from DuckDB catalog."""

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import httpx


def fetch_progress_json(url: str) -> dict | None:
    """Fetch progress JSON from Internet Archive."""
    try:
        response = httpx.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Warning: Failed to fetch {url}: {e}", file=sys.stderr)
    return None


def generate_dashboard_data(db_path: Path, output_path: Path) -> None:
    """Generate dashboard data from DuckDB."""
    con = duckdb.connect(str(db_path), read_only=True)

    # Backfill progress
    result = con.execute("""
        SELECT
            MIN(date) as oldest_date,
            MAX(date) as newest_date,
            COUNT(DISTINCT date) as unique_days,
            COUNT(*) as total_items
        FROM djen_state.coverage
    """).fetchone()

    oldest_date = str(result[0]) if result[0] else None
    newest_date = str(result[1]) if result[1] else None
    unique_days = result[2] or 0
    total_items = result[3] or 0

    target_days = 764  # 2024-01-01 to 2026-02-03
    progress_pct = round((unique_days / target_days * 100), 2) if unique_days > 0 else 0

    # Daily Stats for CalendarHeatmap
    daily_stats = con.execute("""
        SELECT
            date,
            COUNT(*) as count
        FROM djen_state.coverage
        GROUP BY date
        ORDER BY date
    """).fetchall()

    # Recent Activity (last 7 days) for TimelineGraph
    recent_date_limit = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%d")
    recent_activity = con.execute(f"""
        SELECT
            date,
            COUNT(*) as count
        FROM djen_state.coverage
        WHERE date >= '{recent_date_limit}'
        GROUP BY date
        ORDER BY date
    """).fetchall()

    # Tribunal stats
    tribunal_stats = con.execute("""
        SELECT
            tribunal,
            COUNT(*) as count
        FROM djen_state.coverage
        GROUP BY tribunal
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()

    con.close()

    # Fetch progress from Internet Archive
    ia_base = "https://archive.org/download/causaganha-catalog"
    collect_progress = fetch_progress_json(f"{ia_base}/collect-progress.json")
    consolidate_progress = fetch_progress_json(f"{ia_base}/consolidate-progress.json")

    # Fallback to backfill-progress.json if collect-progress not available (backward compatibility)
    if not collect_progress:
        collect_progress = fetch_progress_json(f"{ia_base}/backfill-progress.json")

    data = {
        "collect_progress": collect_progress or {
            "oldest_date": oldest_date,
            "newest_date": newest_date,
            "unique_days": unique_days,
            "total_items": total_items,
            "target_range": {"start": "2024-01-01", "end": "2026-02-03", "total_days": target_days},
            "progress_pct": progress_pct,
            "last_updated": datetime.now(UTC).isoformat(),
        },
        "consolidate_progress": consolidate_progress or {
            "oldest_date": None,
            "newest_date": None,
            "unique_days": 0,
            "total_items": 0,
            "target_range": {"start": "2024-01-01", "end": "2026-02-03", "total_days": target_days},
            "progress_pct": 0.0,
            "last_updated": datetime.now(UTC).isoformat(),
        },
        "backfill_progress": collect_progress or {  # Legacy field for backward compatibility
            "oldest_date": oldest_date,
            "newest_date": newest_date,
            "unique_days": unique_days,
            "total_items": total_items,
            "target_range": {"start": "2024-01-01", "end": "2026-02-03", "total_days": target_days},
            "progress_pct": progress_pct,
            "last_updated": datetime.now(UTC).isoformat(),
            "daily_stats": [{"date": str(d), "count": c} for d, c in daily_stats],
            "recent_activity": [{"date": str(d), "count": c} for d, c in recent_activity],
        },
        "tribunal_stats": [{"tribunal": t, "count": c} for t, c in tribunal_stats],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    db_path = Path("data/causaganha.duckdb")
    output_path = Path("dashboard/public/dashboard-data.json")

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    generate_dashboard_data(db_path, output_path)
