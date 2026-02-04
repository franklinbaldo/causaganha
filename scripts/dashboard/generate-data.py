#!/usr/bin/env python3
"""Generate dashboard-data.json from DuckDB catalog."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb


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

    data = {
        "backfill_progress": {
            "oldest_date": oldest_date,
            "newest_date": newest_date,
            "unique_days": unique_days,
            "total_items": total_items,
            "target_range": {
                "start": "2024-01-01",
                "end": "2026-02-03",
                "total_days": target_days
            },
            "progress_pct": progress_pct,
            "last_updated": datetime.now(UTC).isoformat()
        },
        "tribunal_stats": [
            {"tribunal": t, "count": c} for t, c in tribunal_stats
        ]
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
