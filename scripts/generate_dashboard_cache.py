#!/usr/bin/env python3

FILE_SIZE_THRESHOLD_KB = 1024
SATURDAY_WEEKDAY = 5
QUALITY_THRESHOLD_POOR = 0.26
QUALITY_THRESHOLD_ACCEPTABLE = 0.51
QUALITY_THRESHOLD_GOOD = 0.76

"""Generate dashboard cache JSON files from the catalog manifest.

Reads manifest.parquet (the catalog's index of all IA files) and derives
all dashboard data from it. Falls back to IA metadata API when the manifest
is empty or incomplete.

Data sources:
  - manifest.parquet from causaganha-catalog (one HTTP fetch via DuckDB httpfs)
  - IA search API for item sizes (one HTTP call)
  - IA metadata API for tribunal status fallback (up to 2 HTTP calls)
  - GitHub API for workflow runs (one HTTP call)

Usage:
  python generate_dashboard_cache.py                     # Generate local cache
  python generate_dashboard_cache.py --manifest ./m.parquet  # Use local manifest

Outputs:
  - web/public/cache/meta.json     # Version and timestamp
  - web/public/cache/today.json    # Today's metrics and tribunal status
  - web/public/cache/runs.json     # Recent GitHub Actions runs
  - web/public/cache/calendar.json # Historical calendar data
"""

import argparse
import contextlib
import json
import os
import sys
import tempfile
import tempfile as _tempfile
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from pathlib import Path
from typing import Any

import duckdb


# Configuration
CALENDAR_DAYS = 120
GITHUB_REPO = "franklinbaldo/causaganha"
OUTPUT_DIR = Path(__file__).parent.parent / "web" / "public" / "cache"
MANIFEST_URL = "https://archive.org/download/causaganha-catalog/manifest.parquet"
MANIFEST_JSONL_URL = "https://archive.org/download/causaganha-catalog/manifest.jsonl"
BACKFILL_URL = "https://archive.org/download/causaganha-catalog/backfill-needed.parquet"
IA_SEARCH_URL = (
    "https://archive.org/advancedsearch.php"
    "?q=identifier:djen-*"
    "&fl[]=identifier&fl[]=item_size"
    "&rows=10000&output=json"
)
IA_STATE_URL = "https://archive.org/download/causaganha-dashboard/ia-state.json"

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


def load_absent_coverage_from_ia_state(
    state_path: Path = Path("data/ia-state.json"),
) -> dict[str, list[str]]:
    """Load absent coverage from ia-state.json (local file or IA download URL)."""
    state_data: dict[str, Any] | None = None

    if state_path.exists():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            state_data = json.loads(state_path.read_text(encoding="utf-8"))

    if state_data is None:
        state_data = fetch_json(IA_STATE_URL)

    if not state_data:
        return {}

    entries = state_data.get("entries")
    if not isinstance(entries, dict):
        return {}

    absent_coverage: dict[str, list[str]] = {}
    for date_key, tribunals in entries.items():
        if not isinstance(date_key, str) or not isinstance(tribunals, dict):
            continue
        for tribunal_code, status in tribunals.items():
            if status != "absent" or not isinstance(tribunal_code, str):
                continue
            absent_coverage.setdefault(tribunal_code, []).append(date_key)

    return absent_coverage


def fetch_json(url: str, timeout: int = 30) -> dict[str, Any] | None:
    """Fetch JSON from URL with error handling."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CausaGanha-Dashboard/3.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data: dict[str, Any] = json.loads(response.read().decode())
            return data
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None


def load_manifest(con: duckdb.DuckDBPyConnection, manifest_path: str | None) -> bool:
    """Load manifest into DuckDB, preferring jsonl from URL or parquet if specified."""
    # If a specific path is passed, we assume it's parquet (as in original behavior)
    if manifest_path:
        try:
            con.execute(f"""
                CREATE TABLE manifest AS
                SELECT * FROM read_parquet('{manifest_path}')
            """)
            # Check schema
            schema = [col[0] for col in con.execute("DESCRIBE manifest").fetchall()]
            if "date" not in schema:
                msg = "Missing date column in custom manifest."
                raise ValueError(msg)
            return True
        except Exception:
            return False

    # Otherwise try jsonl first
    try:
        con.execute(f"""
            CREATE TABLE manifest AS
            SELECT
                CAST(date AS VARCHAR) as date,
                CAST(tribunal AS VARCHAR) as tribunal,
                'zip' as file_type,
                NULL as table_name,
                NULL as file_name,
                'djen-' || CAST(date AS VARCHAR) as ia_item,
                CAST(zip_url AS VARCHAR) as ia_url,
                CAST(downloaded_at AS VARCHAR) as created_at
            FROM read_json_auto('{MANIFEST_JSONL_URL}')
        """)
        # Verify it worked and has data
        con.execute("SELECT COUNT(*) FROM manifest").fetchone()
        return True
    except Exception:
        # jsonl failed, fallback to parquet
        pass

    try:
        con.execute(f"""
            CREATE TABLE manifest AS
            SELECT * FROM read_parquet('{MANIFEST_URL}')
        """)

        # Check if manifest has expected schema
        schema = [col[0] for col in con.execute("DESCRIBE manifest").fetchall()]
        if "date" not in schema:
            con.execute("DROP TABLE manifest")
            msg = "Invalid schema"
            raise ValueError(msg)
        con.execute("SELECT COUNT(*) FROM manifest").fetchone()
        return True
    except Exception:
        # Create empty fallback table
        try:
            con.execute("DROP TABLE IF EXISTS manifest")
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


def load_backfill_needed(con: duckdb.DuckDBPyConnection, backfill_path: str | None) -> bool:
    """Load backfill-needed.parquet into DuckDB for progress calculation."""
    source = backfill_path or BACKFILL_URL

    if backfill_path:
        pass
    else:
        pass

    try:
        con.execute(f"""
            CREATE TABLE backfill_needed AS
            SELECT * FROM read_parquet('{source}')
        """)
        con.execute("SELECT COUNT(*) FROM backfill_needed").fetchone()
    except Exception:
        return False
    else:
        return True


def fetch_item_sizes() -> dict[str, int]:
    """Fetch item sizes from IA search API (one bulk request)."""
    data = fetch_json(IA_SEARCH_URL)
    if not data or "response" not in data:
        return {}

    sizes: dict[str, int] = {}
    for doc in data["response"].get("docs", []):
        identifier = doc.get("identifier", "")
        item_size = doc.get("item_size", 0)
        if identifier.startswith("djen-") and identifier != "causaganha-catalog":
            # Strip "djen-" prefix so keys match date lookups (e.g. "2026-03-16")
            date_key = identifier.removeprefix("djen-")
            sizes[date_key] = int(item_size) if item_size else 0

    return sizes


def is_manifest_populated(con: duckdb.DuckDBPyConnection) -> bool:
    """Check if the manifest table has any real data."""
    try:
        count = con.execute(
            "SELECT COUNT(*) FROM manifest WHERE file_type IN ('zip', 'absent')",
        ).fetchone()
        return count is not None and count[0] > 0
    except Exception:
        return False


def generate_pipeline_metrics(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Generate pipeline progress metrics from manifest."""
    if not is_manifest_populated(con):
        return {
            "total_zips": 0,
            "days_consolidated": 0,
            "total_parquets": 0,
            "dates_collected": 0,
            "backfill_total": 0,
            "backfill_done": 0,
            "progress_pct": 0.0,
        }

    try:
        row = con.execute("""
            SELECT
                COUNT(*) FILTER (WHERE file_type = 'zip') as total_zips,
                COUNT(*) FILTER (WHERE file_type = 'parquet') as total_parquets,
                COUNT(DISTINCT date) FILTER (WHERE file_type = 'zip') as dates_collected,
                COUNT(DISTINCT date) FILTER (WHERE file_type = 'parquet') as days_consolidated
            FROM manifest
        """).fetchone()

        total_zips = row[0] if row else 0
        total_parquets = row[1] if row else 0
        dates_collected = row[2] if row else 0
        days_consolidated = row[3] if row else 0

        # Backfill progress: count collected date+tribunal combos vs total expected
        # Both zip and absent count as "done" (absent = checked, no publication)
        done = con.execute(
            "SELECT COUNT(DISTINCT date || '|' || tribunal) FROM manifest WHERE file_type IN ('zip', 'absent')",
        ).fetchone()
        backfill_done = done[0] if done else 0

        # Total expected comes from backfill_needed table if available
        try:
            pending = con.execute(
                "SELECT COUNT(*) FROM backfill_needed",
            ).fetchone()
            backfill_pending = pending[0] if pending else 0
        except Exception:
            # Estimate total from date range: weekdays from 2024-01-01 to yesterday × tribunals

            start = date_type(2024, 1, 1)
            end = datetime.now(UTC).date() - timedelta(days=1)
            weekdays = sum(
                1
                for i in range((end - start).days + 1)
                if (start + timedelta(days=i)).weekday() < SATURDAY_WEEKDAY
            )
            backfill_pending = max(weekdays * len(TRIBUNALS) - backfill_done, 0)

        backfill_total = backfill_done + backfill_pending
        progress_pct = (
            round(100.0 * backfill_done / backfill_total, 1) if backfill_total > 0 else 0.0
        )

        result = {
            "total_zips": total_zips,
            "days_consolidated": days_consolidated,
            "total_parquets": total_parquets,
            "dates_collected": dates_collected,
            "backfill_total": backfill_total,
            "backfill_done": backfill_done,
            "progress_pct": progress_pct,
        }
    except Exception:
        return {
            "total_zips": 0,
            "days_consolidated": 0,
            "total_parquets": 0,
            "dates_collected": 0,
            "backfill_total": 0,
            "backfill_done": 0,
            "progress_pct": 0.0,
        }
    else:
        return result


def query_tribunal_details(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, Any]]:
    """Query per-tribunal last_update date and doc_count from manifest."""
    try:
        rows = con.execute("""
            SELECT
                tribunal,
                MAX(date) as last_update,
                COUNT(*) FILTER (WHERE file_type = 'zip') as doc_count
            FROM manifest
            WHERE file_type IN ('zip', 'absent')
            GROUP BY tribunal
        """).fetchall()
        return {row[0]: {"last_update": row[1], "doc_count": row[2]} for row in rows}
    except Exception:
        return {}


def fetch_ia_pending_tasks() -> dict[str, Any]:
    """Query the IA Tasks API for pending derivation tasks on recent items.

    Returns a dict with pending_count and a list of items with pending tasks.
    The IA Tasks API is free and requires no authentication for public items.
    """
    year = datetime.now(UTC).year
    # Check a few recent items for pending tasks
    pending_items = []
    total_pending = 0
    # Sample a few tribunals to keep API calls low
    sample_tribunals = ["TJSP", "TJRJ", "TJMG", "TRF1", "TRT2"]
    for tribunal in sample_tribunals:
        item_id = f"djen-{tribunal.lower()}-{year}"
        url = f"https://archive.org/services/tasks.php?identifier={item_id}&catalog=1&history=0"
        data = fetch_json(url, timeout=10)
        if data and data.get("value", {}).get("catalog"):
            tasks = data["value"]["catalog"]
            if tasks:
                total_pending += len(tasks)
                pending_items.append({"item": item_id, "tasks": len(tasks)})
    return {
        "pending_count": total_pending,
        "pending_items": pending_items,
        "checked_at": datetime.now(UTC).isoformat(),
    }


def generate_today_cache(con: duckdb.DuckDBPyConnection, sizes: dict[str, int]) -> dict[str, Any]:
    """Generate today's metrics and tribunal status from manifest.
    Fallback to IA metadata API is removed because items are no longer daily.
    """
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")

    manifest_populated = is_manifest_populated(con)

    tribunal_status: dict[str, dict[str, Any]] = {}
    date_used = today

    # Get per-tribunal details (last_update, doc_count) from full manifest
    tribunal_details = query_tribunal_details(con) if manifest_populated else {}

    if manifest_populated:
        # Primary: query manifest for today's tribunal statuses
        result = con.execute(
            """
            SELECT tribunal, file_type
            FROM manifest
            WHERE date = ? AND file_type IN ('zip', 'absent')
        """,
            [today],
        ).fetchall()

        if not result:
            result = con.execute(
                """
                SELECT tribunal, file_type
                FROM manifest
                WHERE date = ? AND file_type IN ('zip', 'absent')
            """,
                [yesterday],
            ).fetchall()
            date_used = yesterday

        if not result:
            # Fallback to the latest available date in the manifest
            latest_date_row = con.execute(
                "SELECT MAX(date) FROM manifest WHERE file_type IN ('zip', 'absent')"
            ).fetchone()
            if latest_date_row and latest_date_row[0]:
                date_used = latest_date_row[0]
                result = con.execute(
                    """
                    SELECT tribunal, file_type
                    FROM manifest
                    WHERE date = ? AND file_type IN ('zip', 'absent')
                """,
                    [date_used],
                ).fetchall()

        for tribunal, file_type in result:
            details = tribunal_details.get(tribunal, {})
            tribunal_status[tribunal] = {
                "status": "ok" if file_type == "zip" else "absent",
                "size": None,
                "last_update": details.get("last_update"),
                "doc_count": details.get("doc_count", 0),
            }

    # Mark missing tribunals as pending (still enrich with historical details)
    for tribunal in TRIBUNALS:
        if tribunal not in tribunal_status:
            details = tribunal_details.get(tribunal, {})
            tribunal_status[tribunal] = {
                "status": "pending",
                "size": None,
                "last_update": details.get("last_update"),
                "doc_count": details.get("doc_count", 0),
            }

    # Calculate metrics
    zip_count = sum(1 for t in tribunal_status.values() if t["status"] == "ok")
    size_today = sizes.get(date_used, 0)  # Fallback to 0

    # Check IA derivation task status (best-effort, don't fail on error)
    ia_tasks = {}
    with contextlib.suppress(Exception):
        ia_tasks = fetch_ia_pending_tasks()

    return {
        "date": date_used,
        "files_today": zip_count,
        "size_today": size_today,
        "tribunal_status": tribunal_status,
        "manifest_available": manifest_populated,
        "ia_tasks": ia_tasks,
    }


def generate_runs_cache() -> dict[str, Any]:
    """Fetch recent GitHub Actions runs."""
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
    """Generate calendar data for last N days from manifest.
    Fallback to IA search is removed.
    """
    manifest_populated = is_manifest_populated(con)

    date_tribunals: dict[str, int] = {}

    if manifest_populated:
        # Primary: query manifest for zip counts per date
        result = con.execute(
            """
            SELECT date, COUNT(DISTINCT tribunal) as tribunal_count
            FROM manifest
            WHERE file_type = 'zip'
              AND date >= ?
            GROUP BY date
        """,
            [(datetime.now(UTC) - timedelta(days=CALENDAR_DAYS)).strftime("%Y-%m-%d")],
        ).fetchall()
        date_tribunals = {row[0]: row[1] for row in result}

    # Build calendar data
    calendar_data: dict[str, dict[str, Any]] = {}
    max_size = 0

    for i in range(CALENDAR_DAYS):
        date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
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
    for entry in calendar_data.values():
        if max_size > 0 and entry["size"] > 0:
            ratio = entry["size"] / max_size
            if ratio >= QUALITY_THRESHOLD_GOOD:
                entry["level"] = 4
            elif ratio >= QUALITY_THRESHOLD_ACCEPTABLE:
                entry["level"] = 3
            elif ratio >= QUALITY_THRESHOLD_POOR:
                entry["level"] = 2
            else:
                entry["level"] = 1
        else:
            entry["level"] = 0

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


def generate_backfill_state_cache() -> dict[str, Any]:
    """Generate backfill state summary from backfill-state.json."""
    state_path = Path("data/backfill-state.json")
    if not state_path.exists():
        state_path = Path("data_backfill_state.json")

    if not state_path.exists():
        return {}

    try:
        with state_path.open() as f:
            state_data = json.load(f)
    except Exception:
        return {}

    tribunals_data = state_data.get("tribunals", {})

    start_dates_path = (
        Path(__file__).parent.parent / "web" / "public" / "tribunal_start_dates.json"
    )
    start_dates = {}
    if start_dates_path.exists():
        try:
            with start_dates_path.open() as f:
                start_dates = json.load(f)
        except Exception:
            pass

    today = datetime.now(UTC).date()
    results = []

    for tribunal, info in tribunals_data.items():
        cursor_str = info.get("cursor_date")
        stopped = info.get("stopped", False)
        empty_streak = info.get("empty_streak", 0)
        last_result = info.get("last_result")

        if stopped:
            state = "Stopped"
        elif last_result == "error":
            state = "Paused"
        else:
            state = "Active"

        genesis_str = start_dates.get(tribunal, "2024-01-01")

        pct = 0.0
        if cursor_str and genesis_str:
            try:
                cursor_d = datetime.strptime(cursor_str, "%Y-%m-%d").date()
                genesis_d = datetime.strptime(genesis_str, "%Y-%m-%d").date()
                total_days = (today - genesis_d).days
                if total_days > 0:
                    completed_days = (today - cursor_d).days
                    raw_pct = completed_days / total_days * 100.0
                    pct = max(0.0, min(100.0, raw_pct))
                else:
                    pct = 100.0
            except ValueError:
                pass

        results.append(
            {
                "tribunal": tribunal,
                "cursor_date": cursor_str,
                "state": state,
                "empty_streak": empty_streak,
                "genesis_date": genesis_str,
                "completion_pct": round(pct, 1),
                "last_result": last_result,
                "last_hit_date": info.get("last_hit_date"),
                "last_checked_at": info.get("last_checked_at"),
            }
        )

    results.sort(key=lambda x: x["tribunal"])
    return {
        "tribunals": results,
        "updated_at": state_data.get("updated_at", datetime.now(UTC).isoformat()),
    }


def generate_backfill_cache(
    con: duckdb.DuckDBPyConnection, sizes: dict[str, int] | None = None
) -> dict[str, Any]:
    """Generate backfill progress data from manifest for ETACard, DualProgressCard, BackfillProgress.

    This is the primary data source for backfill-related dashboard components.
    Unlike generate-data.py (which needs DuckDB artifact), this always works
    because it reads from manifest.parquet.
    """
    if not is_manifest_populated(con):
        return {}

    try:
        # Per-year progress: count distinct date+tribunal combos collected vs expected
        year_rows = con.execute("""
            SELECT
                EXTRACT(YEAR FROM CAST(date AS DATE))::INT as year,
                COUNT(DISTINCT date) as unique_days,
                COUNT(DISTINCT date || '|' || tribunal) FILTER (WHERE file_type IN ('zip', 'absent')) as combos_done,
                COUNT(DISTINCT date || '|' || tribunal) FILTER (WHERE file_type = 'zip') as zips
            FROM manifest
            WHERE file_type IN ('zip', 'absent', 'parquet')
            GROUP BY year
            ORDER BY year
        """).fetchall()

        # Consolidation per year: dates that have parquet files
        cons_rows = con.execute("""
            SELECT
                EXTRACT(YEAR FROM CAST(date AS DATE))::INT as year,
                COUNT(DISTINCT date) as days_consolidated
            FROM manifest
            WHERE file_type = 'parquet'
            GROUP BY year
            ORDER BY year
        """).fetchall()
        cons_by_year = {row[0]: row[1] for row in cons_rows}

        num_tribunals = len(TRIBUNALS)

        # Calculate target_days: total weekdays from earliest manifest date to yesterday
        date_bounds = con.execute("""
            SELECT MIN(date), MAX(date)
            FROM manifest
            WHERE file_type IN ('zip', 'absent')
        """).fetchone()
        if date_bounds and date_bounds[0]:
            bf_start = (
                date_bounds[0]
                if isinstance(date_bounds[0], date_type)
                else datetime.strptime(str(date_bounds[0]), "%Y-%m-%d").date()
            )
            bf_end = min(
                date_bounds[1]
                if isinstance(date_bounds[1], date_type)
                else datetime.strptime(str(date_bounds[1]), "%Y-%m-%d").date(),
                datetime.now(UTC).date() - timedelta(days=1),
            )
            target_days = sum(
                1
                for i in range((bf_end - bf_start).days + 1)
                if (bf_start + timedelta(days=i)).weekday() < 5
            )
        else:
            target_days = 0

        # Coverage map and ETAs
        coverage_rows = con.execute("""
            SELECT tribunal, CAST(date AS VARCHAR) as date_str
            FROM manifest
            WHERE file_type IN ('zip', 'absent', 'parquet')
            ORDER BY tribunal, date
        """).fetchall()

        tribunal_coverage: dict[str, list[str]] = {}
        for t, d in coverage_rows:
            if t not in tribunal_coverage:
                tribunal_coverage[t] = []
            tribunal_coverage[t].append(d)

        # Absent-only coverage map:
        # - Primary source: ia-state.json (authoritative when marker uploads are disabled)
        # - Legacy fallback: manifest .absent markers only when ia-state is unavailable
        tribunal_absent_coverage = load_absent_coverage_from_ia_state()
        if not tribunal_absent_coverage:
            absent_coverage_rows = con.execute("""
                SELECT tribunal, CAST(date AS VARCHAR) as date_str
                FROM manifest
                WHERE file_type = 'absent'
                ORDER BY tribunal, date
            """).fetchall()
            for t, d in absent_coverage_rows:
                if t not in tribunal_absent_coverage:
                    tribunal_absent_coverage[t] = []
                tribunal_absent_coverage[t].append(d)

        # Done coverage = any collected artifact (zip/parquet) + absent state entries
        tribunal_done_coverage: dict[str, list[str]] = {}
        for tribunal_code, dates in tribunal_coverage.items():
            tribunal_done_coverage[tribunal_code] = list(dates)
        for tribunal_code, dates in tribunal_absent_coverage.items():
            tribunal_done_coverage.setdefault(tribunal_code, []).extend(dates)
        tribunal_coverage_sets = {t: set(dates) for t, dates in tribunal_coverage.items()}

        # Velocity over last 14 days
        velocity_date_limit = (datetime.now(UTC) - timedelta(days=14)).strftime("%Y-%m-%d")
        velocity_rows = con.execute(f"""
            SELECT
                tribunal,
                COUNT(DISTINCT date) as velocity_14d
            FROM manifest
            WHERE file_type IN ('zip', 'absent', 'parquet')
              AND CAST(date AS VARCHAR) >= '{velocity_date_limit}'
            GROUP BY tribunal
        """).fetchall()

        velocity_map = dict(velocity_rows)

        # Per-tribunal zip vs absent counts
        type_counts = con.execute("""
            SELECT tribunal, file_type, COUNT(DISTINCT date) as cnt
            FROM manifest
            WHERE file_type IN ('zip', 'absent')
            GROUP BY tribunal, file_type
        """).fetchall()
        zip_counts: dict[str, int] = {}
        absent_counts: dict[str, int] = {}
        for t, ft, cnt in type_counts:
            if ft == "zip":
                zip_counts[t] = cnt
            elif ft == "absent":
                absent_counts[t] = cnt
        for tribunal_code, dates in tribunal_absent_coverage.items():
            absent_counts[tribunal_code] = len(set(dates))

        # Load start dates from tribunal_start_dates.json if available
        start_dates_path = (
            Path(__file__).parent.parent / "web" / "public" / "tribunal_start_dates.json"
        )
        start_dates: dict[str, str | None] = {}
        if start_dates_path.exists():
            with start_dates_path.open() as f:
                start_dates = json.load(f)

        tribunal_etas: dict[str, dict[str, Any]] = {}

        for tribunal in TRIBUNALS:
            coverage_list = tribunal_done_coverage.get(tribunal, [])
            unique_days_t = len(set(coverage_list))
            zip_count = zip_counts.get(tribunal, 0)
            absent_count = absent_counts.get(tribunal, 0)
            collected = zip_count + absent_count
            missing_days = max(0, target_days - unique_days_t)
            velocity_14d = velocity_map.get(tribunal, 0)
            completion_pct = round(100.0 * collected / target_days, 1) if target_days > 0 else 0.0

            eta_days = None
            if missing_days > 0 and velocity_14d > 0:
                velocity_per_day = velocity_14d / 14.0
                eta_days = int(missing_days / velocity_per_day)

            tribunal_etas[tribunal] = {
                "missing_days": missing_days,
                "velocity_14d": velocity_14d,
                "eta_days": eta_days,
                "completion_pct": completion_pct,
                "zip_count": zip_count,
                "absent_days_count": absent_count,
                "genesis_date": start_dates.get(tribunal),
            }

        progress_by_year: dict[str, dict[str, Any]] = {}
        total_unique_days = 0
        total_combos_done = 0
        total_expected = 0
        total_days_consolidated = 0

        for year, unique_days, combos_done, zips in year_rows:
            # Calculate expected weekdays for this year

            year_start = date_type(year, 1, 1)
            year_end = min(
                date_type(year, 12, 31),
                datetime.now(UTC).date() - timedelta(days=1),
            )
            if year_start > year_end:
                continue
            weekdays = sum(
                1
                for i in range((year_end - year_start).days + 1)
                if (year_start + timedelta(days=i)).weekday() < SATURDAY_WEEKDAY
            )
            expected = weekdays * num_tribunals
            pct = round(100.0 * combos_done / expected, 1) if expected > 0 else 0.0
            days_cons = cons_by_year.get(year, 0)

            progress_by_year[str(year)] = {
                "completed": combos_done,
                "total": expected,
                "pct": pct,
                "unique_days": unique_days,
                "weekdays": weekdays,
                "zips": zips,
                "days_consolidated": days_cons,
            }
            total_unique_days += unique_days
            total_combos_done += combos_done
            total_expected += expected
            total_days_consolidated += days_cons

        # Overall dates
        date_range = con.execute("""
            SELECT MIN(date), MAX(date)
            FROM manifest
            WHERE file_type IN ('zip', 'absent')
        """).fetchone()
        oldest_date = date_range[0] if date_range else None
        newest_date = date_range[1] if date_range else None

        total_pct = (
            round(100.0 * total_combos_done / total_expected, 1) if total_expected > 0 else 0.0
        )

        # Daily stats: tribunals collected per date (for CalendarHeatmap)
        daily_rows = con.execute("""
            SELECT date, COUNT(DISTINCT tribunal) as count
            FROM manifest
            WHERE file_type IN ('zip', 'absent')
            GROUP BY date
            ORDER BY date
        """).fetchall()
        daily_map = {str(row[0]): row[1] for row in daily_rows}
        for tribunal_code, dates in tribunal_absent_coverage.items():
            for date_str in set(dates):
                if date_str not in daily_map:
                    daily_map[date_str] = 0
                # Only increment if this tribunal/date is not already counted via manifest
                if date_str not in tribunal_coverage_sets.get(tribunal_code, set()):
                    daily_map[date_str] += 1
        daily_stats = [{"date": day, "count": count} for day, count in sorted(daily_map.items())]

        # Recent activity: last 14 days (for TimelineGraph)
        cutoff = (datetime.now(UTC) - timedelta(days=14)).strftime("%Y-%m-%d")
        recent = [d for d in daily_stats if d["date"] >= cutoff]

        # Per-tribunal reliability: coverage ratio
        tribunal_rows = con.execute("""
            SELECT
                tribunal,
                COUNT(DISTINCT date) FILTER (WHERE file_type = 'zip') as days_with_data,
                COUNT(DISTINCT date) FILTER (WHERE file_type = 'absent') as days_absent,
                COUNT(DISTINCT date) as days_total
            FROM manifest
            WHERE file_type IN ('zip', 'absent')
            GROUP BY tribunal
            ORDER BY days_with_data DESC
        """).fetchall()
        tribunal_stats_map = {
            row[0]: {
                "tribunal": row[0],
                "days_with_data": row[1],
                "days_absent": row[2],
                "days_total": row[3],
            }
            for row in tribunal_rows
        }
        for tribunal_code, dates in tribunal_absent_coverage.items():
            entry = tribunal_stats_map.setdefault(
                tribunal_code,
                {
                    "tribunal": tribunal_code,
                    "days_with_data": 0,
                    "days_absent": 0,
                    "days_total": 0,
                },
            )
            absent_days = len(set(dates))
            entry["days_absent"] = absent_days
            entry["days_total"] = entry["days_with_data"] + absent_days
        tribunal_stats = []
        for row in tribunal_stats_map.values():
            days_total = row["days_total"]
            tribunal_stats.append(
                {
                    **row,
                    "data_rate_pct": round(100.0 * row["days_with_data"] / days_total, 1)
                    if days_total > 0
                    else 0.0,
                }
            )

        # Calculate total archived volume from item sizes
        total_volume_bytes = sum((sizes or {}).values())

        return {
            "progress_by_year": progress_by_year,
            "collect_progress": {
                "oldest_date": oldest_date,
                "newest_date": newest_date,
                "unique_days": total_unique_days,
                "total_items": total_combos_done,
                "target_range": {
                    "start": oldest_date or "2024-01-01",
                    "end": newest_date or datetime.now(UTC).strftime("%Y-%m-%d"),
                    "total_days": total_expected // len(TRIBUNALS) if total_expected > 0 else 0,
                },
                "progress_pct": total_pct,
                "last_updated": datetime.now(UTC).isoformat() + "Z",
            },
            "consolidate_progress": {
                "oldest_date": oldest_date,
                "newest_date": newest_date,
                "unique_days": total_days_consolidated,
                "total_items": 0,
                "target_range": {
                    "start": oldest_date or "2024-01-01",
                    "end": newest_date or datetime.now(UTC).strftime("%Y-%m-%d"),
                    "total_days": total_expected // len(TRIBUNALS) if total_expected > 0 else 0,
                },
                "progress_pct": round(100.0 * total_days_consolidated / total_unique_days, 1)
                if total_unique_days > 0
                else 0.0,
                "last_updated": datetime.now(UTC).isoformat() + "Z",
            },
            "backfill_progress": {
                "oldest_date": oldest_date,
                "newest_date": newest_date,
                "unique_days": total_unique_days,
                "total_items": total_combos_done,
                "target_range": {
                    "start": oldest_date or "2024-01-01",
                    "end": newest_date or datetime.now(UTC).strftime("%Y-%m-%d"),
                    "total_days": total_expected // len(TRIBUNALS) if total_expected > 0 else 0,
                },
                "progress_pct": total_pct,
                "last_updated": datetime.now(UTC).isoformat() + "Z",
                "daily_stats": daily_stats,
                "recent_activity": recent,
            },
            "tribunal_stats": tribunal_stats,
            "tribunal_coverage": {t: list(set(d)) for t, d in tribunal_coverage.items()},
            "tribunal_absent_coverage": {
                t: list(set(d)) for t, d in tribunal_absent_coverage.items()
            },
            "tribunal_etas": tribunal_etas,
            "volume": {
                "total_bytes": total_volume_bytes,
                "total_gb": round(total_volume_bytes / (1024**3), 2),
                "days_with_data": len(sizes or {}),
            },
        }
    except Exception:
        return {}


def format_bytes(size: float) -> str:
    """Format bytes to human readable string."""
    size_f = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_f < FILE_SIZE_THRESHOLD_KB:
            return f"{size_f:.1f} {unit}"
        size_f /= 1024
    return f"{size_f:.1f} TB"


def generate_rss_feed(
    today_data: dict[str, Any],
    runs_data: dict[str, Any],
    calendar_data: dict[str, Any],
) -> str:
    """Generate RSS feed with status updates."""
    now = datetime.now(UTC)
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


IA_DASHBOARD_ITEM = "causaganha-dashboard"


def upload_dashboard_to_ia(files: dict[str, Any]) -> bool:
    """Upload dashboard cache JSON files to Internet Archive."""
    import subprocess

    tmp_dir = Path(tempfile.mkdtemp())
    file_paths = []
    for filename, data in files.items():
        path = tmp_dir / filename
        with path.open("w") as f:
            json.dump(data, f, separators=(",", ":"))
        file_paths.append(str(path))

    try:
        result = subprocess.run(
            [
                "ia",
                "upload",
                IA_DASHBOARD_ITEM,
                *file_paths,
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
            timeout=120,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def main() -> None:
    """Generate all cache files from catalog manifest."""
    parser = argparse.ArgumentParser(description="Generate dashboard cache from catalog manifest")
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="Path to local manifest.parquet (default: download from IA)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload cache JSONs to Internet Archive item causaganha-dashboard",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize DuckDB with httpfs for remote parquet access
    con = duckdb.connect()
    if not args.manifest:
        with contextlib.suppress(Exception):
            con.execute("INSTALL httpfs; LOAD httpfs;")

    # Step 1: Load manifest (one HTTP request or local file)
    manifest_path = args.manifest
    if not manifest_path:
        # Try to download manifest via urllib if httpfs failed
        try:
            con.execute(
                "SELECT 1 FROM duckdb_extensions() WHERE extension_name = 'httpfs' AND loaded",
            )
        except Exception:
            # httpfs not available, download manually

            tmp = Path(tempfile.mkdtemp()) / "manifest.parquet"
            urllib.request.urlretrieve(MANIFEST_URL, str(tmp))
            manifest_path = str(tmp)

    if not load_manifest(con, manifest_path):
        sys.exit(1)

    # Load backfill-needed for progress calculation (non-fatal if missing)
    backfill_path = None
    if manifest_path:
        # If manifest was downloaded manually, also download backfill

        tmp_bf = Path(_tempfile.mkdtemp()) / "backfill-needed.parquet"
        # Try local file first, then IA (which may have CDN propagation delay)
        local_bf = Path("catalog/backfill-needed.parquet")
        if local_bf.exists():
            tmp_bf = local_bf
        else:
            try:
                urllib.request.urlretrieve(BACKFILL_URL, str(tmp_bf))
            except Exception:
                print(f"Warning: backfill-needed.parquet unavailable: {BACKFILL_URL}")
                tmp_bf = None
        backfill_path = str(tmp_bf) if tmp_bf is not None else None
    load_backfill_needed(con, backfill_path)

    manifest_populated = is_manifest_populated(con)
    data_source = "manifest.parquet" if manifest_populated else "IA metadata API (fallback)"

    # Step 2: Fetch item sizes from IA search API (one HTTP request)
    sizes = fetch_item_sizes()

    # Step 3: Generate all caches
    today_data = generate_today_cache(con, sizes)
    runs_data = generate_runs_cache()
    calendar_data = generate_calendar_cache(con, sizes)
    pipeline_metrics = generate_pipeline_metrics(con)
    backfill_data = generate_backfill_cache(con, sizes)
    backfill_state_data = generate_backfill_state_cache()

    con.close()

    # Step 4: Assemble and write

    # Add days_archived, health, and pipeline metrics to today data
    today_data["days_archived"] = calendar_data["stats"]["days_with_data"]
    today_data["health"] = runs_data["health"]
    today_data["pipeline"] = pipeline_metrics

    # Load per-run stats from pipeline orchestrator (if available)
    run_stats_path = os.getenv("PIPELINE_RUN_STATS")
    if run_stats_path:
        try:
            with Path(run_stats_path).open() as f:
                today_data["last_run"] = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Generate metadata
    meta = {
        "version": "3.1",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "source": data_source,
        "calendar_days": CALENDAR_DAYS,
        "manifest_available": manifest_populated,
    }

    # Load omission stats if available locally
    omission_data = None
    omission_path = Path("catalog/omission_stats.json")
    if omission_path.exists():
        try:
            with omission_path.open() as f:
                omission_data = json.load(f)
        except json.JSONDecodeError:
            pass

    # Write local files
    files: dict[str, Any] = {
        "meta.json": meta,
        "today.json": today_data,
        "runs.json": runs_data,
        "calendar.json": calendar_data,
    }
    if backfill_data:
        files["backfill.json"] = backfill_data
    if backfill_state_data:
        files["backfill_state.json"] = backfill_state_data
    if omission_data:
        files["omission_stats.json"] = omission_data

    for filename, data in files.items():
        path = OUTPUT_DIR / filename
        with path.open("w") as f:
            json.dump(data, f, separators=(",", ":"))
        _ = path.stat().st_size

    # Generate RSS feed
    rss_content = generate_rss_feed(today_data, runs_data, calendar_data)
    rss_path = OUTPUT_DIR / "feed.xml"
    with rss_path.open("w") as f:
        f.write(rss_content)

    # Upload to Internet Archive for live dashboard access
    if args.upload:
        if upload_dashboard_to_ia(files):
            pass
        else:
            pass


if __name__ == "__main__":
    main()
