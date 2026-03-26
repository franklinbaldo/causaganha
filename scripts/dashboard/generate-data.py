#!/usr/bin/env python3
"""Generate dashboard-data.json from DuckDB catalog."""

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from causaganha.storage.connection import get_connection


def fetch_progress_json(url: str) -> dict | None:
    """Fetch progress JSON from Internet Archive."""
    response = httpx.get(url, timeout=30)
    if response.status_code == 200:
        return response.json()
    return None


def generate_dashboard_data(db_path: Path, output_path: Path) -> None:
    """Generate dashboard data from DuckDB."""
    # Use singleton connection via Ibis backend, access raw DuckDB connection
    backend = get_connection(str(db_path), read_only=True)
    con = backend.con

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

    # Per-tribunal coverage and stats
    coverage_rows = con.execute("""
        SELECT
            tribunal,
            date
        FROM djen_state.coverage
        ORDER BY tribunal, date
    """).fetchall()

    tribunal_coverage = {}
    for t, d in coverage_rows:
        date_str = str(d)
        if t not in tribunal_coverage:
            tribunal_coverage[t] = []
        tribunal_coverage[t].append(date_str)

    # Velocity over last 14 days
    velocity_date_limit = (datetime.now(UTC) - timedelta(days=14)).strftime("%Y-%m-%d")
    velocity_rows = con.execute(f"""
        SELECT
            tribunal,
            COUNT(DISTINCT date) as velocity_14d
        FROM djen_state.coverage
        WHERE date >= '{velocity_date_limit}'
        GROUP BY tribunal
    """).fetchall()

    velocity_map = {t: v for t, v in velocity_rows}

    tribunal_etas = {}
    from datetime import date

    end_date_obj = date(2026, 2, 3)  # Based on target range end 2026-02-03
    start_date_obj = date(2024, 1, 1)
    # The true count of expected days is `target_days` (764)
    # Actually, we should count missing days within the date range from target_start to today, or just total target_days

    for tribunal in list(set(t for t, _ in coverage_rows)):
        coverage_list = tribunal_coverage.get(tribunal, [])
        # Only count unique dates in the target range? Let's just use unique total since target_days is fixed
        # to simplify, assume all dates in coverage are valid
        unique_days_t = len(set(coverage_list))
        missing_days = max(0, target_days - unique_days_t)
        velocity_14d = velocity_map.get(tribunal, 0)

        eta_days = None
        if missing_days > 0 and velocity_14d > 0:
            velocity_per_day = velocity_14d / 14.0
            eta_days = int(missing_days / velocity_per_day)

        tribunal_etas[tribunal] = {
            "missing_days": missing_days,
            "velocity_14d": velocity_14d,
            "eta_days": eta_days,
        }

    # Fetch progress from Internet Archive
    ia_base = "https://archive.org/download/causaganha-catalog"
    collect_progress = fetch_progress_json(f"{ia_base}/collect-progress.json")
    consolidate_progress = fetch_progress_json(f"{ia_base}/consolidate-progress.json")

    # Fallback to backfill-progress.json if collect-progress not available (backward compatibility)
    if not collect_progress:
        collect_progress = fetch_progress_json(f"{ia_base}/backfill-progress.json")

    daily_stats_list = [{"date": str(d), "count": c} for d, c in daily_stats]
    recent_activity_list = [{"date": str(d), "count": c} for d, c in recent_activity]

    db_progress = {
        "oldest_date": oldest_date,
        "newest_date": newest_date,
        "unique_days": unique_days,
        "total_items": total_items,
        "target_range": {"start": "2024-01-01", "end": "2026-02-03", "total_days": target_days},
        "progress_pct": progress_pct,
        "last_updated": datetime.now(UTC).isoformat(),
    }

    # Build backfill_progress: merge IA progress with DuckDB-derived daily breakdowns.
    # daily_stats and recent_activity always come from DuckDB since IA doesn't produce them.
    backfill_base = collect_progress or db_progress
    backfill_progress = {
        **backfill_base,
        "daily_stats": daily_stats_list,
        "recent_activity": recent_activity_list,
    }

    data = {
        "collect_progress": collect_progress or db_progress,
        "consolidate_progress": consolidate_progress
        or {
            "oldest_date": None,
            "newest_date": None,
            "unique_days": 0,
            "total_items": 0,
            "target_range": {"start": "2024-01-01", "end": "2026-02-03", "total_days": target_days},
            "progress_pct": 0.0,
            "last_updated": datetime.now(UTC).isoformat(),
        },
        "backfill_progress": backfill_progress,
        "tribunal_coverage": tribunal_coverage,
        "tribunal_etas": tribunal_etas,
        "target_range": {"start": "2024-01-01", "end": "2026-02-03", "total_days": target_days},
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    db_path = Path("data/causaganha.duckdb")
    output_path = Path("dashboard/public/dashboard-data.json")

    if not db_path.exists():
        sys.exit(1)

    generate_dashboard_data(db_path, output_path)
