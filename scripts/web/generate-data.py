#!/usr/bin/env python3
"""Generate dashboard-data.json from DuckDB catalog."""

import contextlib
import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx

from causaganha.config import TRIBUNAIS
from causaganha.storage.connection import get_connection


logger = logging.getLogger(__name__)

HTTP_200_OK = 200
POOR_SCORE_THRESHOLD = 60
ACCEPTABLE_SCORE_THRESHOLD = 70
GOOD_SCORE_THRESHOLD = 80
EXCELLENT_SCORE_THRESHOLD = 90
MAX_GAP_DAYS = 7
MIN_DISTINCT_DATES = 2
MIN_DAYS_OLD_FOR_CATEGORY = 30


def calculate_quality_scores(
    tribunal_coverage: dict, tribunal_start_dates: dict, end_date_str: str
) -> dict:
    """Calculate quality scores per tribunal based on completeness, recency, and consistency."""
    scores = {}

    end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=UTC).date()
    today_date = datetime.now(UTC).date()
    # Use today as end date if end_date_str is in the future
    end_date_obj = min(end_date_obj, today_date)

    for tribunal, coverage_dates in tribunal_coverage.items():
        if tribunal not in tribunal_start_dates:
            continue

        start_date_str = tribunal_start_dates[tribunal]
        try:
            start_date_obj = (
                datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=UTC).date()
            )
        except ValueError:
            continue

        expected_days = (end_date_obj - start_date_obj).days + 1
        if expected_days <= 0:
            continue

        sorted_dates = sorted(
            [
                datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=UTC).date()
                for d in set(coverage_dates)
            ]
        )
        days_with_data = len(sorted_dates)

        # 1. Completeness (40%)
        completeness = min(100.0, (days_with_data / expected_days) * 100.0)

        # 2. Recency (30%)
        if not sorted_dates:
            recency = 0.0
        else:
            max_date = sorted_dates[-1]
            days_old = (end_date_obj - max_date).days
            if days_old <= 0:
                recency = 100.0
            elif days_old >= MIN_DAYS_OLD_FOR_CATEGORY:
                recency = 0.0
            else:
                # Linear interpolation
                recency = 100.0 * (1.0 - (days_old / 30.0))

        # 3. Consistency (30%)
        if len(sorted_dates) < MIN_DISTINCT_DATES:
            consistency = 0.0 if expected_days > 1 else 100.0
        else:
            num_gaps = 0
            total_periods = len(sorted_dates) - 1
            for i in range(total_periods):
                gap_days = (sorted_dates[i + 1] - sorted_dates[i]).days - 1
                if gap_days > 0:
                    # Penalize >7 day gaps heavily by counting them as multiple gaps
                    if gap_days > MAX_GAP_DAYS:
                        num_gaps += 1 + (gap_days // 7)
                    else:
                        num_gaps += 1

            # Prevent negative consistency
            gap_frequency = min(1.0, num_gaps / total_periods)
            consistency = (1.0 - gap_frequency) * 100.0

        # Score calculation
        score = (completeness * 0.4) + (recency * 0.3) + (consistency * 0.3)

        # Grade mapping
        if score >= EXCELLENT_SCORE_THRESHOLD:
            grade = "A"
        elif score >= GOOD_SCORE_THRESHOLD:
            grade = "B"
        elif score >= ACCEPTABLE_SCORE_THRESHOLD:
            grade = "C"
        elif score >= POOR_SCORE_THRESHOLD:
            grade = "D"
        else:
            grade = "F"

        scores[tribunal] = {
            "score": round(score, 1),
            "grade": grade,
            "completeness": round(completeness, 1),
            "recency": round(recency, 1),
            "consistency": round(consistency, 1),
        }

    return scores


def fetch_progress_json(url: str) -> dict | None:
    """Fetch progress JSON from Internet Archive."""
    response = httpx.get(url, timeout=30)
    if response.status_code == HTTP_200_OK:
        return response.json()
    return None


def generate_dashboard_data(db_path: Path, output_path: Path) -> None:
    """Generate dashboard data from DuckDB."""
    # Attempt to get a connection; handle missing database by skipping DB-bound queries
    try:
        backend = get_connection(str(db_path), read_only=True)
        con = backend.con
    except RuntimeError as e:
        logger.warning("Failed to get database connection: %s", e)
        con = None

    # Get stats from DB only if connected
    oldest_date = None
    newest_date = None
    unique_days = 0
    total_items = 0

    if con:
        try:
            result = con.execute("""
                SELECT
                    MIN(date) as oldest_date,
                    MAX(date) as newest_date,
                    COUNT(DISTINCT date) as unique_days,
                    COUNT(*) as total_items
                FROM djen_state.coverage
            """).fetchone()

            if result:
                oldest_date = str(result[0]) if result[0] else None
                newest_date = str(result[1]) if result[1] else None
                unique_days = result[2] or 0
                total_items = result[3] or 0
        except RuntimeError as e:
            logger.warning("Failed to fetch coverage statistics from database: %s", e)

    target_days = 764  # 2024-01-01 to 2026-02-03
    progress_pct = round((unique_days / target_days * 100), 2) if unique_days > 0 else 0

    # Read tribunal start dates
    start_dates_path = output_path.parent / "tribunal_start_dates.json"
    tribunal_start_dates = {}
    if start_dates_path.exists():
        with contextlib.suppress(Exception):
            tribunal_start_dates = json.loads(start_dates_path.read_text())

    daily_stats = []
    recent_activity = []
    coverage_rows = []
    velocity_rows = []

    if con:
        try:
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
            recent_activity = con.execute(
                """
                SELECT
                    date,
                    COUNT(*) as count
                FROM djen_state.coverage
                WHERE date >= ?
                GROUP BY date
                ORDER BY date
            """,
                [recent_date_limit],
            ).fetchall()

            # Per-tribunal coverage and stats
            coverage_rows = con.execute("""
                SELECT
                    tribunal,
                    date
                FROM djen_state.coverage
                ORDER BY tribunal, date
            """).fetchall()

            # Velocity over last 14 days
            velocity_date_limit = (datetime.now(UTC) - timedelta(days=14)).strftime("%Y-%m-%d")
            velocity_rows = con.execute(
                """
                SELECT
                    tribunal,
                    COUNT(DISTINCT date) as velocity_14d
                FROM djen_state.coverage
                WHERE date >= ?
                GROUP BY tribunal
                ORDER BY tribunal
            """,
                [velocity_date_limit],
            ).fetchall()
        except RuntimeError as e:
            logger.warning("Failed to fetch coverage data from database: %s", e)

    tribunal_coverage = {}
    for t, d in coverage_rows:
        date_str = str(d)
        if t not in tribunal_coverage:
            tribunal_coverage[t] = []
        tribunal_coverage[t].append(date_str)

    velocity_map = dict(velocity_rows)

    # Read backfill state (cursors and streaks)
    backfill_state_path = Path("data/backfill-state.json")
    backfill_cursors = {}
    if backfill_state_path.exists():
        try:
            bs = json.loads(backfill_state_path.read_text())
            for t, info in bs.get("tribunals", {}).items():
                backfill_cursors[t] = {
                    "cursor_date": info.get("cursor_date"),
                    "stopped": info.get("stopped", False),
                    "empty_streak": info.get("empty_streak", 0),
                }
        except (OSError, ValueError) as e:
            logger.warning("Failed to read backfill state from %s: %s", backfill_state_path, e)

    # Read backfill state from state.json (authoritative for both uploaded and absent)
    state_json_path = Path("data/state.json")
    tribunal_absent_coverage = {}
    if state_json_path.exists():
        try:
            sj = json.loads(state_json_path.read_text())
            entries = sj.get("entries", {})
            for date_key, tribunals in entries.items():
                for tcode, status in tribunals.items():
                    if status == "absent":
                        if tcode not in tribunal_absent_coverage:
                            tribunal_absent_coverage[tcode] = []
                        tribunal_absent_coverage[tcode].append(date_key)
                    elif status == "uploaded":
                        if tcode not in tribunal_coverage:
                            tribunal_coverage[tcode] = []
                        if date_key not in tribunal_coverage[tcode]:
                            tribunal_coverage[tcode].append(date_key)
        except (OSError, ValueError) as e:
            logger.warning("Failed to read tribunal state from %s: %s", state_json_path, e)

    # --- RECALCULATE GLOBAL STATS FROM MERGED COVERAGE ---
    all_dates = set()
    total_items = 0
    for dates in tribunal_coverage.values():
        all_dates.update(dates)
        total_items += len(dates)

    unique_days = len(all_dates)
    if all_dates:
        sorted_all = sorted(all_dates)
        oldest_date = sorted_all[0]
        newest_date = sorted_all[-1]

    progress_pct = round((unique_days / target_days * 100), 2) if unique_days > 0 else 0

    tribunal_etas = {}

    date(2026, 2, 3)  # Based on target range end 2026-02-03
    start_date_obj = date(2024, 1, 1)
    # The true count of expected days is `target_days` (764)
    # Actually, we count missing days within the target date range, using total target_days.

    # The set of tribunals to report on: either from DB or from the canonical list
    all_tribunals = {t for t, _ in coverage_rows} if coverage_rows else set(backfill_cursors.keys())
    if not all_tribunals:
        all_tribunals = set(TRIBUNAIS)

    today = datetime.now(UTC).date()

    # Load discovered start dates for dynamic calculation
    discovered_start_dates = {}
    genesis_path = output_path.parent / "tribunal_start_dates.json"
    if genesis_path.exists():
        with contextlib.suppress(Exception):
            discovered_start_dates = json.loads(genesis_path.read_text())

    for tribunal in sorted(all_tribunals):
        coverage_list = tribunal_coverage.get(tribunal, [])
        absent_list = tribunal_absent_coverage.get(tribunal, [])
        unique_days_t = len(set(coverage_list))
        absent_days_t = len(set(absent_list))

        # Determine the anchor date for this tribunal
        # Priority: Discovered Genesis > Hardcoded Start Date > Jan 1st 2024
        start_date_str = (
            discovered_start_dates.get(tribunal)
            or tribunal_start_dates.get(tribunal)
            or "2024-01-01"
        )

        try:
            start_date_obj = (
                datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=UTC).date()
            )
        except ValueError:
            start_date_obj = date(2024, 1, 1)

        total_days_since_genesis = (today - start_date_obj).days + 1
        missing_days = max(0, total_days_since_genesis - unique_days_t - absent_days_t)

        velocity_14d = velocity_map.get(tribunal, 0)

        eta_days = None
        if missing_days > 0 and velocity_14d > 0:
            velocity_per_day = velocity_14d / 14.0
            eta_days = int(missing_days / velocity_per_day)

        # Include backfill state if available
        cursor_info = backfill_cursors.get(tribunal, {})
        tribunal_etas[tribunal] = {
            "missing_days": missing_days,
            "velocity_14d": velocity_14d,
            "eta_days": eta_days,
            "cursor_date": cursor_info.get("cursor_date"),
            "stopped": cursor_info.get("stopped", False),
            "empty_streak": cursor_info.get("empty_streak", 0),
            "genesis_date": start_date_str,
            "absent_days_count": absent_days_t,
            "completion_pct": round(
                ((unique_days_t + absent_days_t) / total_days_since_genesis) * 100, 1
            )
            if total_days_since_genesis > 0
            else 0,
        }

    # Calculate Data Quality Scores
    scores_path = output_path.parent / "tribunal_quality_scores.json"
    quality_scores = calculate_quality_scores(tribunal_coverage, tribunal_start_dates, "2026-02-03")
    scores_path.write_text(json.dumps(quality_scores, ensure_ascii=False, indent=2))

    # Calculate Performance Metrics
    metrics_path = output_path.parent / "perf-metrics.json"
    perf_metrics = {
        "causaganha_collect_latency_ms": [],
        "causaganha_upload_success_rate": 0,
        "causaganha_active_tribunals": len(tribunal_start_dates),
        "causaganha_backlog_pending_days": 0,
        "slowest_tribunals": [],
    }

    total_missing_days = sum(eta.get("missing_days", 0) for eta in tribunal_etas.values())
    perf_metrics["causaganha_backlog_pending_days"] = total_missing_days

    # Calculate slowest tribunals based on lowest velocity
    sorted_tribunals = sorted(
        [(t, v["velocity_14d"]) for t, v in tribunal_etas.items() if v.get("missing_days", 0) > 0],
        key=lambda x: x[1],
    )
    perf_metrics["slowest_tribunals"] = [
        {"tribunal": t, "velocity_14d": v} for t, v in sorted_tribunals[:5]
    ]

    run_stats_path = Path("run_stats.json")
    if run_stats_path.exists():
        try:
            runs = json.loads(run_stats_path.read_text())
            success_count = sum(1 for r in runs if r.get("conclusion") == "success")
            if runs:
                perf_metrics["causaganha_upload_success_rate"] = round(
                    (success_count / len(runs)) * 100, 2
                )

            latencies = []
            for r in runs:
                if r.get("createdAt"):
                    # Mock latency: run_stats.json lacks 'updatedAt', so use fixed values
                    # based on conclusion when the field is absent.
                    if r.get("updatedAt"):
                        start = datetime.strptime(r["createdAt"], "%Y-%m-%dT%H:%M:%SZ").replace(
                            tzinfo=UTC
                        )
                        end = datetime.strptime(r["updatedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(
                            tzinfo=UTC
                        )
                        latency_ms = int((end - start).total_seconds() * 1000)
                    else:
                        latency_ms = (
                            1200000 if r.get("conclusion") == "success" else 300000
                        )  # 20 mins or 5 mins

                    if latency_ms > 0:
                        latencies.append(
                            {
                                "date": r["createdAt"],
                                "latency_ms": latency_ms,
                                "status": r.get("conclusion"),
                            }
                        )
            if latencies:
                perf_metrics["causaganha_collect_latency_ms"] = latencies
        except (OSError, ValueError) as e:
            logger.warning("Failed to read performance metrics from %s: %s", run_stats_path, e)

    metrics_path.write_text(json.dumps(perf_metrics, ensure_ascii=False, indent=2))

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
        "tribunal_absent_coverage": tribunal_absent_coverage,
        "tribunal_etas": tribunal_etas,
        "target_range": {"start": "2024-01-01", "end": "2026-02-03", "total_days": target_days},
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    db_path = Path("data/causaganha.duckdb")
    output_path = Path("web/public/dashboard-data.json")

    # No exit if DB is missing; let get_connection handle it
    generate_dashboard_data(db_path, output_path)
