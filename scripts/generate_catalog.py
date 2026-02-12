#!/usr/bin/env python3
"""Generate CausaGanha catalog for Internet Archive.

Creates:
- manifest.parquet: Index of all files in IA
- backfill-needed.parquet: What's missing from DJEN
- catalog.sql: SQL with remote views
- catalog.duckdb: Ready-to-use DuckDB file
- collect-progress.json + .jsonl: Download progress (current + history)
- consolidate-progress.json + .jsonl: Consolidation progress (current + history)

Usage:
    python scripts/generate_catalog.py --upload
    python scripts/generate_catalog.py --output ./catalog/
"""

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import duckdb
import structlog

from causaganha.config import TRIBUNAIS


logger = structlog.get_logger()

# DJEN started around 2020, but most data is from 2024+
DJEN_START_DATE = date(2024, 1, 1)

IA_CATALOG_ITEM = "causaganha-catalog"

# Known table names from consolidation output
KNOWN_TABLE_NAMES = {
    "comunicacoes",
    "textos",
    "destinatarios",
    "partes",
    "advogados",
    "comunicacao_advogados",
}

# Cache for tribunal stopped checks (tribunal -> date -> bool)
_TRIBUNAL_STOPPED_CACHE: dict[str, dict[str, bool]] = {}


def append_progress_jsonl(path: Path, data: dict) -> None:
    """Append progress data to JSONL file for historical tracking.

    JSONL format allows trivial comparison (tail -2) and historical analysis.
    Each line is a complete JSON object with timestamp.
    """
    try:
        with path.open("a") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        logger.info("jsonl_appended", path=str(path))
    except Exception as e:
        logger.warning("jsonl_append_failed", path=str(path), error=str(e))


def run_ia_command(args: list[str], timeout: int = 300) -> str:
    """Run ia CLI command and return output.

    Returns empty string on error instead of raising exception.
    """
    try:
        result = subprocess.run(
            ["ia", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.warning("ia_command_failed", args=args, stderr=result.stderr[:200])
            return ""
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.warning("ia_command_timeout", args=args)
        return ""
    except FileNotFoundError:
        logger.error("ia_cli_not_found")
        return ""
    except Exception as e:
        logger.warning("ia_command_error", error=str(e))
        return ""


def list_ia_items() -> list[str]:
    """List all djen-* items from Internet Archive.

    Returns empty list on error - caller should handle gracefully.
    """
    logger.info("listing_ia_items")
    output = run_ia_command(["search", "identifier:djen-20*", "--itemlist"])

    if not output:
        logger.warning("no_items_found_or_error")
        return []

    items = [line.strip() for line in output.splitlines() if line.strip()]

    # Validate item format
    valid_items = [item for item in items if item.startswith("djen-")]
    if len(valid_items) < len(items):
        logger.warning("filtered_invalid_items", original=len(items), valid=len(valid_items))

    logger.info("found_items", count=len(valid_items))
    return valid_items


def list_item_files(item_id: str) -> list[dict]:
    """List all files in an IA item with metadata.

    Returns empty list on error - allows processing to continue with other items.
    """
    if not item_id or not item_id.startswith("djen-"):
        logger.warning("invalid_item_id", item_id=item_id)
        return []

    output = run_ia_command(["list", item_id])

    if not output:
        logger.debug("no_files_for_item", item_id=item_id)
        return []

    files = []
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            # ia list output format varies, parse filename safely
            parts = line.strip().split()
            filename = parts[-1] if parts else ""
            if filename and filename.endswith((".zip", ".parquet", ".absent")):
                files.append({"name": filename, "item": item_id})
        except Exception:
            # Skip malformed lines
            continue

    return files


def _validate_date_str(date_str: str) -> bool:
    """Validate date string is a valid YYYY-MM-DD date."""
    import re

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False
    try:
        year, month, day = map(int, date_str.split("-"))
        # Basic sanity checks
        if year < 2020 or year > 2030:
            return False
        if month < 1 or month > 12:
            return False
        if day < 1 or day > 31:
            return False
        return True
    except ValueError:
        return False


def _validate_tribunal_code(tribunal: str) -> bool:
    """Validate tribunal code format."""
    import re

    # Tribunal codes: 2-10 uppercase letters/numbers, may include dashes (e.g. TRE-AC)
    return bool(re.match(r"^[A-Z0-9][A-Z0-9-]{1,9}$", tribunal.upper()))


def get_local_coverage(con: duckdb.DuckDBPyConnection) -> set[tuple[str, str]]:
    """Get set of (date, tribunal) present in local DB."""
    try:
        # Check if table exists
        con.execute("SELECT 1 FROM djen_state.coverage LIMIT 1")
        result = con.execute(
            "SELECT CAST(date AS VARCHAR), tribunal FROM djen_state.coverage"
        ).fetchall()
        return {(str(r[0]), str(r[1])) for r in result}
    except duckdb.CatalogException:
        return set()
    except Exception as e:
        logger.warning("local_coverage_fetch_failed", error=str(e))
        return set()


def generate_collect_progress(con: duckdb.DuckDBPyConnection) -> dict:
    """Generate download (collect) progress metrics for dashboard.

    Based on djen_state.coverage table (what was downloaded/attempted).
    """
    # Check if table exists
    try:
        con.execute("SELECT 1 FROM djen_state.coverage LIMIT 1")
    except duckdb.CatalogException:
        # Table doesn't exist, return empty stats
        return {
            "oldest_date": None,
            "newest_date": None,
            "unique_days": 0,
            "total_items": 0,
            "target_range": {"start": "2024-01-01", "end": "2026-02-03", "total_days": 764},
            "progress_pct": 0.0,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    result = con.execute("""
        SELECT
            MIN(date) as oldest_date,
            MAX(date) as newest_date,
            COUNT(DISTINCT date) as unique_days,
            COUNT(*) as total_items
        FROM djen_state.coverage
    """).fetchone()

    target_start = date(2024, 1, 1)
    target_end = date(2026, 2, 3)
    target_days = (target_end - target_start).days + 1

    oldest_date = result[0] or None
    newest_date = result[1] or None
    unique_days = result[2] or 0
    total_items = result[3] or 0

    progress_pct = (unique_days / target_days * 100) if unique_days > 0 else 0

    return {
        "oldest_date": str(oldest_date) if oldest_date else None,
        "newest_date": str(newest_date) if newest_date else None,
        "unique_days": unique_days,
        "total_items": total_items,
        "target_range": {
            "start": str(target_start),
            "end": str(target_end),
            "total_days": target_days,
        },
        "progress_pct": round(progress_pct, 2),
        "last_updated": datetime.now(UTC).isoformat(),
    }


def generate_consolidate_progress(manifest: list[dict]) -> dict:
    """Generate consolidation progress metrics for dashboard.

    Based on manifest data (what parquets were consolidated and uploaded to IA).
    """
    target_start = date(2024, 1, 1)
    target_end = date(2026, 2, 3)
    target_days = (target_end - target_start).days + 1

    # Find dates with consolidated parquets or _consolidated.marker
    consolidated_dates = set()
    for m in manifest:
        if m["file_type"] == "parquet" or (
            m["file_type"] == "marker" and "_consolidated" in m.get("filename", "")
        ):
            consolidated_dates.add(m["date"])

    if not consolidated_dates:
        return {
            "oldest_date": None,
            "newest_date": None,
            "unique_days": 0,
            "total_items": 0,
            "target_range": {
                "start": str(target_start),
                "end": str(target_end),
                "total_days": target_days,
            },
            "progress_pct": 0.0,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    dates_list = sorted(consolidated_dates)
    oldest_date = dates_list[0]
    newest_date = dates_list[-1]
    unique_days = len(consolidated_dates)

    # Count total consolidated items (parquet files)
    total_items = sum(1 for m in manifest if m["file_type"] == "parquet")

    progress_pct = (unique_days / target_days * 100) if unique_days > 0 else 0

    return {
        "oldest_date": oldest_date,
        "newest_date": newest_date,
        "unique_days": unique_days,
        "total_items": total_items,
        "target_range": {
            "start": str(target_start),
            "end": str(target_end),
            "total_days": target_days,
        },
        "progress_pct": round(progress_pct, 2),
        "last_updated": datetime.now(UTC).isoformat(),
    }


def parse_filename(filename: str, item_id: str) -> dict | None:
    """Parse filename to extract date, tribunal, file_type, table_name.

    Returns None for invalid/malformed filenames - allows processing to continue.
    """
    # Basic validation
    if not filename or not isinstance(filename, str):
        return None

    # Expected: djen-2026-01-15-TJSP.zip or djen-2026-01-15-TJSP-comunicacoes.parquet
    if not filename.startswith("djen-"):
        return None

    # Validate file extension
    if not filename.endswith((".zip", ".parquet", ".absent")):
        return None

    parts = (
        filename.replace("djen-", "")
        .replace(".zip", "")
        .replace(".parquet", "")
        .replace(".absent", "")
    )

    if filename.endswith(".zip"):
        # djen-2026-01-15-TJSP.zip -> date=2026-01-15, tribunal=TJSP
        # djen-2026-01-15-TRE-AC.zip -> date=2026-01-15, tribunal=TRE-AC
        try:
            # Format: YYYY-MM-DD-TRIBUNAL (tribunal may contain dashes, e.g. TRE-AC)
            split_parts = parts.split("-")
            if len(split_parts) < 4:
                return None
            date_str = "-".join(split_parts[:3])
            tribunal = "-".join(split_parts[3:])  # Join all remaining parts

            # Validate date and tribunal
            if not _validate_date_str(date_str):
                return None
            if not _validate_tribunal_code(tribunal):
                return None

            return {
                "date": date_str,
                "tribunal": tribunal.upper(),
                "file_type": "zip",
                "table_name": None,
                "file_name": filename,
                "ia_item": item_id,
                "ia_url": f"https://archive.org/download/{item_id}/{filename}",
            }
        except (IndexError, ValueError):
            return None

    elif filename.endswith(".absent"):
        # djen-2026-01-15-TJSP.absent -> date=2026-01-15, tribunal=TJSP
        # djen-2026-01-15-TRE-AC.absent -> date=2026-01-15, tribunal=TRE-AC
        try:
            split_parts = parts.split("-")
            if len(split_parts) < 4:
                return None
            date_str = "-".join(split_parts[:3])
            tribunal = "-".join(split_parts[3:])  # Join all remaining parts

            if not _validate_date_str(date_str):
                return None
            if not _validate_tribunal_code(tribunal):
                return None

            return {
                "date": date_str,
                "tribunal": tribunal.upper(),
                "file_type": "absent",
                "table_name": None,
                "file_name": filename,
                "ia_item": item_id,
                "ia_url": f"https://archive.org/download/{item_id}/{filename}",
            }
        except (IndexError, ValueError):
            return None

    elif filename.endswith(".parquet"):
        # djen-2026-01-15-TJSP-comunicacoes.parquet
        # djen-2026-01-15-TRE-AC-comunicacoes.parquet (tribunal with dash)
        try:
            # Format: YYYY-MM-DD-TRIBUNAL-table (tribunal may contain dashes)
            split_parts = parts.split("-")
            if len(split_parts) < 5:
                return None
            date_str = "-".join(split_parts[:3])

            # Find table name by checking from end (table names are known)
            table_name = None
            tribunal_end_idx = len(split_parts)
            for i in range(len(split_parts) - 1, 2, -1):
                candidate = "-".join(split_parts[i:])
                if candidate in KNOWN_TABLE_NAMES:
                    table_name = candidate
                    tribunal_end_idx = i
                    break
                # Also check single part
                if split_parts[i] in KNOWN_TABLE_NAMES:
                    table_name = split_parts[i]
                    tribunal_end_idx = i
                    break

            if not table_name:
                return None  # Unknown table format

            tribunal = "-".join(split_parts[3:tribunal_end_idx])

            # Validate date and tribunal
            if not _validate_date_str(date_str):
                return None
            if not _validate_tribunal_code(tribunal):
                return None

            return {
                "date": date_str,
                "tribunal": tribunal.upper(),
                "file_type": "parquet",
                "table_name": table_name,
                "file_name": filename,
                "ia_item": item_id,
                "ia_url": f"https://archive.org/download/{item_id}/{filename}",
            }
        except (IndexError, ValueError):
            return None

    return None


def load_existing_manifest() -> list[dict]:
    """Load existing manifest from Internet Archive.

    Returns empty list if not found or error.
    """
    manifest_url = f"https://archive.org/download/{IA_CATALOG_ITEM}/manifest.parquet"
    logger.info("loading_existing_manifest", url=manifest_url)

    try:
        # Use a temporary duckdb connection to read from URL
        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")

        # Check if file exists by trying to describe it
        try:
            con.execute(f"DESCRIBE SELECT * FROM read_parquet('{manifest_url}')")
        except Exception:
            logger.info("no_existing_manifest_found_at_url")
            return []

        # Fetch records
        df = con.execute(f"SELECT * FROM read_parquet('{manifest_url}')").df()
        con.close()

        records = df.to_dict("records")
        logger.info("loaded_existing_manifest", records=len(records))
        return records
    except Exception as e:
        logger.warning("load_manifest_failed", error=str(e))
        return []


def get_item_date(item_id: str) -> date | None:
    """Extract date from item identifier (e.g. djen-2026-01-06)."""
    if not item_id.startswith("djen-"):
        return None
    try:
        # djen-YYYY-MM-DD
        date_str = item_id.replace("djen-", "")[:10]
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None


def generate_manifest(items: list[str], existing_manifest: list[dict] | None = None) -> list[dict]:
    """Generate manifest of all files in Internet Archive.

    If existing_manifest is provided, performs incremental listing:
    - Lists new items
    - Re-lists items from the last 14 days
    - Re-lists items that lack parquets but have ZIPs (pending consolidation)
    """
    logger.info("generating_manifest", items=len(items), incremental=bool(existing_manifest))

    # Group existing entries by item for fast lookup
    existing_by_item = {}
    if existing_manifest:
        for m in existing_manifest:
            item = m.get("ia_item")
            if not item:
                continue
            if item not in existing_by_item:
                existing_by_item[item] = []
            existing_by_item[item].append(m)

    items_to_list = []
    manifest = []

    today = datetime.now(tz=UTC).date()
    # Items from the last 14 days are always re-listed to catch updates
    recency_threshold = timedelta(days=14)

    for item_id in items:
        item_date = get_item_date(item_id)

        # Determine if we should re-list this item
        should_list = False
        reason = ""

        if item_id not in existing_by_item:
            should_list = True
            reason = "new_item"
        # Check if it's recent
        elif item_date and (today - item_date) < recency_threshold:
            should_list = True
            reason = "recent_date"
        else:
            # Check if it lacks parquets but has zips
            # (means it might be pending consolidation)
            files = existing_by_item[item_id]
            has_zip = any(f.get("file_type") == "zip" for f in files)
            has_parquet = any(f.get("file_type") == "parquet" for f in files)

            if has_zip and not has_parquet:
                should_list = True
                reason = "pending_consolidation"

        if should_list:
            items_to_list.append(item_id)
            logger.debug("item_queued_for_listing", item=item_id, reason=reason)
        else:
            # Use existing entries
            manifest.extend(existing_by_item[item_id])

    if not items_to_list:
        logger.info("no_items_to_list_incremental")
        return manifest

    logger.info("items_to_list", count=len(items_to_list), total=len(items))
    completed_count = 0

    # Parallelize file listing to speed up catalog generation
    # Uses 16 workers to fetch file lists concurrently
    with ThreadPoolExecutor(max_workers=16) as executor:
        future_to_item = {
            executor.submit(list_item_files, item_id): item_id for item_id in items_to_list
        }

        for future in as_completed(future_to_item):
            item_id = future_to_item[future]
            try:
                files = future.result()
                for f in files:
                    parsed = parse_filename(f["name"], item_id)
                    if parsed:
                        parsed["created_at"] = datetime.now(tz=UTC).isoformat()
                        manifest.append(parsed)
            except Exception as e:
                logger.error("manifest_item_failed", item=item_id, error=str(e))

            completed_count += 1
            if completed_count % 50 == 0:
                logger.info("progress", current=completed_count, total=len(items_to_list))

    logger.info("manifest_complete", files=len(manifest))
    return manifest


def _is_tribunal_stopped(
    tribunal: str, target_date: date, manifest: list[dict], absent_threshold: int = 60
) -> bool:
    """Check if a tribunal has been absent for 60+ consecutive days before target_date.

    Scans the last N days (absent_threshold) backward from target_date using manifest data.
    Returns True if tribunal is consistently absent (all days have .absent marker).

    Uses in-memory cache to avoid redundant checks.
    """
    date_str = target_date.strftime("%Y-%m-%d")

    # Check cache
    if tribunal in _TRIBUNAL_STOPPED_CACHE:
        if date_str in _TRIBUNAL_STOPPED_CACHE[tribunal]:
            return _TRIBUNAL_STOPPED_CACHE[tribunal][date_str]
    else:
        _TRIBUNAL_STOPPED_CACHE[tribunal] = {}

    # Build lookup from manifest for efficient checking
    tribunal_files = {}
    for m in manifest:
        if m["tribunal"] == tribunal:
            d = m["date"]
            if d not in tribunal_files:
                tribunal_files[d] = []
            tribunal_files[d].append(m["file_type"])

    # Check last N days
    for days_back in range(1, absent_threshold + 1):
        check_date = target_date - timedelta(days=days_back)
        if check_date.weekday() >= 5:  # skip weekends
            continue

        check_date_str = check_date.strftime("%Y-%m-%d")

        # If date not in manifest at all, can't conclude stopped
        if check_date_str not in tribunal_files:
            result = False
            _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
            return result

        # If we find a .zip (not just .absent), tribunal is active
        if "zip" in tribunal_files[check_date_str]:
            result = False
            _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
            return result

        # If neither zip nor absent, can't conclude stopped
        if "absent" not in tribunal_files[check_date_str]:
            result = False
            _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
            return result

    # All checked days had .absent marker - tribunal is stopped
    result = True
    _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
    return result


def generate_backfill_list(
    manifest: list[dict],
    start_date: date,
    end_date: date,
    local_coverage: set[tuple[str, str]] | None = None,
) -> list[dict]:
    """Determine what's missing from DJEN.

    Merges coverage from IA manifest (remote) and local DuckDB (local_coverage).
    Excludes tribunals that have been stopped (60+ consecutive days absent).
    """
    logger.info(
        "generating_backfill_list",
        start=start_date,
        end=end_date,
        local_items=len(local_coverage) if local_coverage else 0,
    )

    # Build set of collected (date, tribunal) pairs (zip or absent = collected)
    collected = set()
    for m in manifest:
        if m["file_type"] in ("zip", "absent"):
            collected.add((m["date"], m["tribunal"]))

    # Merge local coverage
    if local_coverage:
        collected.update(local_coverage)

    logger.info("collected_combinations", count=len(collected))

    # Generate all expected combinations, excluding stopped tribunals
    backfill = []
    stopped_count = 0
    current = start_date
    while current <= end_date:
        # Skip weekends (courts don't publish on weekends)
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            date_str = current.strftime("%Y-%m-%d")
            for tribunal in TRIBUNAIS:
                if (date_str, tribunal) not in collected:
                    # Skip if tribunal is stopped (60+ days absent)
                    if _is_tribunal_stopped(tribunal, current, manifest):
                        stopped_count += 1
                        continue

                    backfill.append(
                        {
                            "date": date_str,
                            "tribunal": tribunal,
                            "reason": "not_collected",
                            "last_checked": datetime.now(tz=UTC).isoformat(),
                        },
                    )
        current += timedelta(days=1)

    logger.info(
        "backfill_needed",
        count=len(backfill),
        stopped_excluded=stopped_count,
    )
    return backfill


def generate_catalog_sql(manifest: list[dict]) -> str:
    """Generate SQL with remote views."""
    logger.info("generating_catalog_sql")

    # Group parquet files by table
    tables = {}
    for m in manifest:
        if m["file_type"] == "parquet" and m["table_name"]:
            table = m["table_name"]
            if table not in tables:
                tables[table] = []
            tables[table].append(m["ia_url"])

    sql_parts = [
        "-- ============================================",
        "-- CausaGanha Remote Catalog",
        f"-- Generated: {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "-- ============================================",
        "",
        "-- Install and load httpfs for remote access",
        "INSTALL httpfs;",
        "LOAD httpfs;",
        "",
        "-- Manifest table (index of all files)",
        "CREATE TABLE IF NOT EXISTS manifest AS",
        f"SELECT * FROM read_parquet('https://archive.org/download/{IA_CATALOG_ITEM}/manifest.parquet');",
        "",
        "-- Backfill needed (what's missing)",
        "CREATE TABLE IF NOT EXISTS backfill_needed AS",
        f"SELECT * FROM read_parquet('https://archive.org/download/{IA_CATALOG_ITEM}/backfill-needed.parquet');",
        "",
        "-- ============================================",
        "-- REMOTE VIEWS (query directly from IA)",
        "-- ============================================",
        "",
    ]

    # Create view for each table type
    for table_name, urls in sorted(tables.items()):
        if len(urls) > 0:
            # Limit URLs to avoid too long SQL
            sample_urls = urls[:100]  # First 100 for view definition
            urls_str = ",\n    ".join(f"'{u}'" for u in sample_urls)

            sql_parts.extend(
                [
                    f"-- {table_name}: {len(urls)} files",
                    f"CREATE OR REPLACE VIEW {table_name} AS",
                    "SELECT * FROM read_parquet([",
                    f"    {urls_str}",
                    "]);",
                    "",
                ],
            )

    # Add helper views
    sql_parts.extend(
        [
            "-- ============================================",
            "-- HELPER VIEWS",
            "-- ============================================",
            "",
            "-- Collection status by date",
            "CREATE OR REPLACE VIEW collection_status AS",
            "SELECT",
            "    date,",
            "    COUNT(DISTINCT tribunal) as tribunals_collected,",
            "    SUM(CASE WHEN file_type = 'zip' THEN 1 ELSE 0 END) as zip_files,",
            "    SUM(CASE WHEN file_type = 'parquet' THEN 1 ELSE 0 END) as parquet_files",
            "FROM manifest",
            "GROUP BY date",
            "ORDER BY date DESC;",
            "",
            "-- Backfill progress",
            "CREATE OR REPLACE VIEW backfill_progress AS",
            "SELECT",
            "    (SELECT COUNT(DISTINCT date || tribunal) FROM manifest WHERE file_type = 'zip') as collected,",
            "    (SELECT COUNT(*) FROM backfill_needed) as pending,",
            "    ROUND(100.0 * (SELECT COUNT(DISTINCT date || tribunal) FROM manifest WHERE file_type = 'zip') /",
            "        ((SELECT COUNT(DISTINCT date || tribunal) FROM manifest WHERE file_type = 'zip') +",
            "         (SELECT COUNT(*) FROM backfill_needed)), 2) as percent_complete;",
            "",
        ],
    )

    return "\n".join(sql_parts)


def create_catalog_duckdb(
    manifest: list[dict],
    backfill: list[dict],
    sql: str,
    output_dir: Path,
) -> Path | None:
    """Create ready-to-use DuckDB file.

    Returns None on error - caller should handle gracefully.
    """
    logger.info("creating_catalog_duckdb")

    db_path = output_dir / "catalog.duckdb"

    try:
        con = duckdb.connect(str(db_path))
    except Exception as e:
        logger.error("duckdb_connection_failed", path=str(db_path), error=str(e))
        return None

    try:
        # Install httpfs
        con.execute("INSTALL httpfs;")
        con.execute("LOAD httpfs;")

        # Create manifest table from data
        con.execute("""
            CREATE TABLE IF NOT EXISTS manifest (
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

        # Clear existing data if table already existed
        con.execute("DELETE FROM manifest;")

        for m in manifest:
            # Safe extraction with defaults for missing keys
            con.execute(
                "INSERT INTO manifest VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    m.get("date", ""),
                    m.get("tribunal", ""),
                    m.get("file_type", ""),
                    m.get("table_name"),
                    m.get("file_name", ""),
                    m.get("ia_item", ""),
                    m.get("ia_url", ""),
                    m.get("created_at", ""),
                ],
            )

        # Create backfill table
        con.execute("""
            CREATE TABLE IF NOT EXISTS backfill_needed (
                date VARCHAR,
                tribunal VARCHAR,
                reason VARCHAR,
                last_checked VARCHAR
            )
        """)

        # Clear existing data if table already existed
        con.execute("DELETE FROM backfill_needed;")

        for b in backfill:
            con.execute(
                "INSERT INTO backfill_needed VALUES (?, ?, ?, ?)",
                [
                    b.get("date", ""),
                    b.get("tribunal", ""),
                    b.get("reason", ""),
                    b.get("last_checked", ""),
                ],
            )

        # Create helper views
        con.execute("DROP VIEW IF EXISTS collection_status;")
        con.execute("""
            CREATE VIEW collection_status AS
            SELECT
                date,
                COUNT(DISTINCT tribunal) as tribunals_collected,
                SUM(CASE WHEN file_type = 'zip' THEN 1 ELSE 0 END) as zip_files,
                SUM(CASE WHEN file_type = 'parquet' THEN 1 ELSE 0 END) as parquet_files
            FROM manifest
            GROUP BY date
            ORDER BY date DESC
        """)

        con.execute("DROP VIEW IF EXISTS backfill_progress;")
        con.execute("""
            CREATE VIEW backfill_progress AS
            SELECT
                (SELECT COUNT(DISTINCT date || tribunal) FROM manifest WHERE file_type = 'zip') as collected,
                (SELECT COUNT(*) FROM backfill_needed) as pending,
                ROUND(100.0 * (SELECT COUNT(DISTINCT date || tribunal) FROM manifest WHERE file_type = 'zip') /
                    NULLIF((SELECT COUNT(DISTINCT date || tribunal) FROM manifest WHERE file_type = 'zip') +
                     (SELECT COUNT(*) FROM backfill_needed), 0), 2) as percent_complete
        """)

        con.close()
        logger.info("duckdb_created", path=str(db_path))
        return db_path

    except Exception as e:
        logger.error("duckdb_creation_failed", error=str(e))
        try:
            con.close()
        except Exception:
            pass
        return None


def save_parquet(data: list[dict], output_path: Path) -> bool:
    """Save data as parquet using DuckDB.

    Returns True on success, False on error.
    """
    try:
        if not data:
            # Create empty parquet with schema
            con = duckdb.connect()
            con.execute(
                f"COPY (SELECT NULL as dummy WHERE FALSE) TO '{output_path}' (FORMAT PARQUET)",
            )
            con.close()
            return True

        con = duckdb.connect()

        # Create table from dict
        columns = list(data[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        col_defs = ", ".join([f"{c} VARCHAR" for c in columns])

        con.execute("DROP TABLE IF EXISTS temp;")
        con.execute(f"CREATE TABLE temp ({col_defs})")

        for row in data:
            values = [str(row.get(c, "")) if row.get(c) is not None else None for c in columns]
            con.execute(f"INSERT INTO temp VALUES ({placeholders})", values)

        con.execute(f"COPY temp TO '{output_path}' (FORMAT PARQUET)")
        con.close()
        return True

    except Exception as e:
        logger.error("save_parquet_failed", path=str(output_path), error=str(e))
        return False


def upload_to_ia(files: list[Path]) -> bool:
    """Upload catalog files to Internet Archive."""
    logger.info("uploading_to_ia", files=[f.name for f in files])

    file_args = [str(f) for f in files]

    try:
        result = subprocess.run(
            ["ia", "upload", IA_CATALOG_ITEM]
            + file_args
            + [
                "--metadata=collection:opensource",
                "--metadata=mediatype:data",
                "--metadata=title:CausaGanha Catalog",
                "--metadata=description:Master catalog for CausaGanha DJEN data. Contains manifest of all files and views for remote queries.",
                "--metadata=subject:causaganha;djen;legal;brazil;catalog",
                "--metadata=creator:CausaGanha",
                "--retries=3",
                "--no-derive",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:
            logger.info("upload_success")
            return True
        logger.error("upload_failed", stderr=result.stderr)
        return False

    except subprocess.TimeoutExpired:
        logger.error("upload_timeout")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate CausaGanha catalog")
    parser.add_argument("--output", type=str, default="./catalog", help="Output directory")
    parser.add_argument("--upload", action="store_true", help="Upload to Internet Archive")
    parser.add_argument(
        "--full", action="store_true", help="Force full catalog rebuild (disable incremental)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start date for backfill (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date for backfill (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print(f"Error: Cannot create output directory {output_dir} (permission denied)")
        return 1
    except OSError as e:
        print(f"Error: Cannot create output directory {output_dir}: {e}")
        return 1

    # Date range for backfill calculation with validation
    try:
        if args.start_date:
            if not _validate_date_str(args.start_date):
                print(f"Error: Invalid start date format: {args.start_date} (expected YYYY-MM-DD)")
                return 1
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        else:
            start_date = DJEN_START_DATE

        if args.end_date:
            if not _validate_date_str(args.end_date):
                print(f"Error: Invalid end date format: {args.end_date} (expected YYYY-MM-DD)")
                return 1
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        else:
            end_date = date.today() - timedelta(days=1)
    except ValueError as e:
        print(f"Error: Invalid date: {e}")
        return 1

    if start_date > end_date:
        print(f"Error: Start date {start_date} is after end date {end_date}")
        return 1

    print("Generating catalog...")
    print(f"  Output: {output_dir}")
    print(f"  Backfill range: {start_date} to {end_date}")
    print(f"  Mode: {'Full' if args.full else 'Incremental'}")
    print()

    # 1. List all IA items
    items = list_ia_items()
    print(f"Found {len(items)} items on Internet Archive")

    # 2. Try to load existing manifest if in incremental mode
    existing_manifest = None
    if not args.full:
        existing_manifest = load_existing_manifest()

    # 3. Generate manifest
    manifest = generate_manifest(items, existing_manifest)
    print(f"Manifest: {len(manifest)} files indexed")

    # 4. Get local coverage and generate backfill list
    local_coverage = set()
    main_db_path = Path("data/causaganha.duckdb")

    if main_db_path.exists():
        try:
            con = duckdb.connect(str(main_db_path), read_only=True)
            local_coverage = get_local_coverage(con)
            con.close()
            print(f"Local state: {len(local_coverage)} items found in database")
        except Exception as e:
            logger.warning("local_state_read_failed", error=str(e))

    backfill = generate_backfill_list(manifest, start_date, end_date, local_coverage)
    print(f"Backfill needed: {len(backfill)} date/tribunal combinations")

    # 4. Generate SQL
    sql = generate_catalog_sql(manifest)

    # 5. Save files
    manifest_path = output_dir / "manifest.parquet"
    backfill_path = output_dir / "backfill-needed.parquet"
    sql_path = output_dir / "catalog.sql"

    if not save_parquet(manifest, manifest_path):
        print(f"Error: Failed to save {manifest_path}")
        return 1
    print(f"Saved: {manifest_path}")

    if not save_parquet(backfill, backfill_path):
        print(f"Error: Failed to save {backfill_path}")
        return 1
    print(f"Saved: {backfill_path}")

    try:
        sql_path.write_text(sql)
        print(f"Saved: {sql_path}")
    except OSError as e:
        print(f"Error: Failed to save {sql_path}: {e}")
        return 1

    # Generate backfill progress metrics for dashboard
    logger.info("generating_backfill_progress")

    # We need to connect to the main DB to get coverage stats
    # It might not exist if running fresh, handle gracefully
    main_db_path = Path("data/causaganha.duckdb")
    # Generate collect progress (downloads)
    collect_progress_path = None
    if main_db_path.exists():
        try:
            # Open read-only
            con = duckdb.connect(str(main_db_path), read_only=True)
            collect_data = generate_collect_progress(con)
            con.close()

            # Save current state (JSON)
            collect_progress_path = output_dir / "collect-progress.json"
            collect_progress_path.write_text(json.dumps(collect_data, ensure_ascii=False, indent=2))
            logger.info("collect_progress_saved", path=str(collect_progress_path))
            print(f"Saved: {collect_progress_path}")

            # Append to history (JSONL)
            collect_history_path = output_dir / "collect-progress.jsonl"
            append_progress_jsonl(collect_history_path, collect_data)
            print(f"Appended: {collect_history_path}")
        except Exception as e:
            logger.error("collect_progress_failed", error=str(e))
    else:
        logger.warning("main_db_not_found", path=str(main_db_path))

    # Generate consolidate progress (parquets)
    consolidate_data = generate_consolidate_progress(manifest)

    # Save current state (JSON)
    consolidate_progress_path = output_dir / "consolidate-progress.json"
    consolidate_progress_path.write_text(json.dumps(consolidate_data, ensure_ascii=False, indent=2))
    logger.info("consolidate_progress_saved", path=str(consolidate_progress_path))
    print(f"Saved: {consolidate_progress_path}")

    # Append to history (JSONL)
    consolidate_history_path = output_dir / "consolidate-progress.jsonl"
    append_progress_jsonl(consolidate_history_path, consolidate_data)
    print(f"Appended: {consolidate_history_path}")

    # Keep backfill-progress.json for backward compatibility (alias to collect)
    if main_db_path.exists():
        try:
            backfill_progress_path = output_dir / "backfill-progress.json"
            backfill_progress_path.write_text(
                json.dumps(collect_data, ensure_ascii=False, indent=2)
            )
            logger.info("backfill_progress_saved_legacy", path=str(backfill_progress_path))
            print(f"Saved: {backfill_progress_path} (legacy, alias to collect-progress.json)")
        except Exception:
            pass

    # 6. Create DuckDB
    db_path = create_catalog_duckdb(manifest, backfill, sql, output_dir)
    if db_path is None:
        print("Error: Failed to create DuckDB catalog")
        return 1
    print(f"Saved: {db_path}")

    # 7. Upload if requested
    if args.upload:
        print()
        print("Uploading to Internet Archive...")
        files = [manifest_path, backfill_path, sql_path, db_path]

        # Add progress files if they exist (JSON + JSONL)
        if collect_progress_path and collect_progress_path.exists():
            files.append(collect_progress_path)
        collect_history_path = output_dir / "collect-progress.jsonl"
        if collect_history_path.exists():
            files.append(collect_history_path)

        if consolidate_progress_path and consolidate_progress_path.exists():
            files.append(consolidate_progress_path)
        consolidate_history_path = output_dir / "consolidate-progress.jsonl"
        if consolidate_history_path.exists():
            files.append(consolidate_history_path)

        # Legacy backfill-progress.json for backward compatibility
        legacy_progress = output_dir / "backfill-progress.json"
        if legacy_progress.exists():
            files.append(legacy_progress)

        success = upload_to_ia(files)
        if success:
            print(f"Uploaded to https://archive.org/details/{IA_CATALOG_ITEM}")
        else:
            print("Upload failed!")
            return 1

    # Summary
    print()
    print("=" * 60)
    print("CATALOG SUMMARY")
    print("=" * 60)

    zip_count = len([m for m in manifest if m["file_type"] == "zip"])
    parquet_count = len([m for m in manifest if m["file_type"] == "parquet"])
    dates_collected = len(set(m["date"] for m in manifest if m["file_type"] == "zip"))

    total_expected = len(backfill) + zip_count
    percent_complete = (zip_count / total_expected * 100) if total_expected > 0 else 0

    print("Collected:")
    print(f"  - {zip_count} ZIP files")
    print(f"  - {parquet_count} Parquet files")
    print(f"  - {dates_collected} unique dates")
    print()
    print("Backfill needed:")
    print(f"  - {len(backfill)} date/tribunal combinations")
    print()
    print(f"Progress: {percent_complete:.1f}% complete")
    print()
    print(f"Catalog URL: https://archive.org/download/{IA_CATALOG_ITEM}/catalog.duckdb")

    # Set GitHub Actions output: catalog was successfully rebuilt
    import os

    catalog_updated = True  # If we got here without error, catalog was updated
    print(f"\n  Catalog updated: {catalog_updated}")

    # Output for GitHub Actions conditional triggers
    if os_env := os.getenv("GITHUB_OUTPUT"):
        with open(os_env, "a") as f:
            f.write(f"catalog_updated={'true' if catalog_updated else 'false'}\n")
            f.write(f"catalog_manifest={len(manifest)}\n")
            f.write(f"catalog_backfill={len(backfill)}\n")
            f.write(f"catalog_zips={zip_count}\n")
            f.write(f"catalog_parquets={parquet_count}\n")
            f.write(f"catalog_dates={dates_collected}\n")
            f.write(f"catalog_progress={percent_complete:.1f}\n")

    return 0


if __name__ == "__main__":
    exit(main())
