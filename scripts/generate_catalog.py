#!/usr/bin/env python3
"""Generate CausaGanha catalog for Internet Archive.

Creates:
- manifest.parquet: Index of all files in IA
- backfill-needed.parquet: What's missing from DJEN
- catalog.sql: SQL with remote views
- catalog.duckdb: Ready-to-use DuckDB file

Usage:
    python scripts/generate_catalog.py --upload
    python scripts/generate_catalog.py --output ./catalog/
"""

import argparse
import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import duckdb
import structlog


logger = structlog.get_logger()

# All 91 Brazilian courts
TRIBUNAIS = [
    # Federal
    "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6",
    # Superior
    "STF", "STJ", "TST", "TSE", "STM", "CNJ", "CNMP", "TNU",
    # State (27)
    "TJAC", "TJAL", "TJAM", "TJAP", "TJBA", "TJCE", "TJDF", "TJES",
    "TJGO", "TJMA", "TJMG", "TJMS", "TJMT", "TJPA", "TJPB", "TJPE",
    "TJPI", "TJPR", "TJRJ", "TJRN", "TJRO", "TJRR", "TJRS", "TJSC",
    "TJSE", "TJSP", "TJTO",
    # Labor (24)
    "TRT1", "TRT2", "TRT3", "TRT4", "TRT5", "TRT6", "TRT7", "TRT8",
    "TRT9", "TRT10", "TRT11", "TRT12", "TRT13", "TRT14", "TRT15",
    "TRT16", "TRT17", "TRT18", "TRT19", "TRT20", "TRT21", "TRT22",
    "TRT23", "TRT24",
    # Electoral (27)
    "TREAC", "TREAL", "TREAM", "TREAP", "TREBA", "TRECE", "TREDF",
    "TREES", "TREGO", "TREMA", "TREMG", "TREMS", "TREMT", "TREPA",
    "TREPB", "TREPE", "TREPI", "TREPR", "TRERJ", "TRERN", "TRERO",
    "TRERR", "TRERS", "TRESC", "TRESE", "TRESP", "TRETO",
]

# DJEN started around 2020, but most data is from 2024+
DJEN_START_DATE = date(2024, 1, 1)

IA_CATALOG_ITEM = "causaganha-catalog"


def run_ia_command(args: list[str]) -> str:
    """Run ia CLI command and return output."""
    result = subprocess.run(
        ["ia", *args],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result.stdout


def list_ia_items() -> list[str]:
    """List all djen-* items from Internet Archive."""
    logger.info("listing_ia_items")
    output = run_ia_command(["search", "identifier:djen-20*", "--itemlist"])
    items = [line.strip() for line in output.splitlines() if line.strip()]
    logger.info("found_items", count=len(items))
    return items


def list_item_files(item_id: str) -> list[dict]:
    """List all files in an IA item with metadata."""
    output = run_ia_command(["list", item_id, "--all", "--glob", "*.{zip,parquet}"])

    files = []
    for line in output.splitlines():
        if not line.strip():
            continue
        # ia list output format varies, parse filename
        filename = line.strip().split()[-1] if line.strip() else ""
        if filename.endswith((".zip", ".parquet")):
            files.append({"name": filename, "item": item_id})

    return files


def parse_filename(filename: str, item_id: str) -> dict | None:
    """Parse filename to extract date, tribunal, file_type, table_name."""
    # Expected: djen-2026-01-15-TJSP.zip or djen-2026-01-15-TJSP-comunicacoes.parquet
    if not filename.startswith("djen-"):
        return None

    parts = filename.replace("djen-", "").replace(".zip", "").replace(".parquet", "")

    if filename.endswith(".zip"):
        # djen-2026-01-15-TJSP.zip -> date=2026-01-15, tribunal=TJSP
        try:
            # Format: YYYY-MM-DD-TRIBUNAL
            date_str = "-".join(parts.split("-")[:3])
            tribunal = parts.split("-")[3]
            return {
                "date": date_str,
                "tribunal": tribunal,
                "file_type": "zip",
                "table_name": None,
                "file_name": filename,
                "ia_item": item_id,
                "ia_url": f"https://archive.org/download/{item_id}/{filename}",
            }
        except (IndexError, ValueError):
            return None

    elif filename.endswith(".parquet"):
        # djen-2026-01-15-TJSP-comunicacoes.parquet
        try:
            # Format: YYYY-MM-DD-TRIBUNAL-table
            date_str = "-".join(parts.split("-")[:3])
            rest = "-".join(parts.split("-")[3:])
            # rest = TJSP-comunicacoes
            tribunal = rest.split("-")[0]
            table_name = "-".join(rest.split("-")[1:])
            return {
                "date": date_str,
                "tribunal": tribunal,
                "file_type": "parquet",
                "table_name": table_name,
                "file_name": filename,
                "ia_item": item_id,
                "ia_url": f"https://archive.org/download/{item_id}/{filename}",
            }
        except (IndexError, ValueError):
            return None

    return None


def generate_manifest(items: list[str]) -> list[dict]:
    """Generate manifest of all files in Internet Archive."""
    logger.info("generating_manifest", items=len(items))

    manifest = []
    for i, item_id in enumerate(items):
        if i % 10 == 0:
            logger.info("progress", current=i, total=len(items))

        files = list_item_files(item_id)
        for f in files:
            parsed = parse_filename(f["name"], item_id)
            if parsed:
                parsed["created_at"] = datetime.now(tz=UTC).isoformat()
                manifest.append(parsed)

    logger.info("manifest_complete", files=len(manifest))
    return manifest


def generate_backfill_list(manifest: list[dict], start_date: date, end_date: date) -> list[dict]:
    """Determine what's missing from DJEN."""
    logger.info("generating_backfill_list", start=start_date, end=end_date)

    # Build set of collected (date, tribunal) pairs
    collected = set()
    for m in manifest:
        if m["file_type"] == "zip":
            collected.add((m["date"], m["tribunal"]))

    logger.info("collected_combinations", count=len(collected))

    # Generate all expected combinations
    backfill = []
    current = start_date
    while current <= end_date:
        # Skip weekends (courts don't publish on weekends)
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            date_str = current.strftime("%Y-%m-%d")
            for tribunal in TRIBUNAIS:
                if (date_str, tribunal) not in collected:
                    backfill.append({
                        "date": date_str,
                        "tribunal": tribunal,
                        "reason": "not_collected",
                        "last_checked": datetime.now(tz=UTC).isoformat(),
                    })
        current += timedelta(days=1)

    logger.info("backfill_needed", count=len(backfill))
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

            sql_parts.extend([
                f"-- {table_name}: {len(urls)} files",
                f"CREATE OR REPLACE VIEW {table_name} AS",
                "SELECT * FROM read_parquet([",
                f"    {urls_str}",
                "]);",
                "",
            ])

    # Add helper views
    sql_parts.extend([
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
    ])

    return "\n".join(sql_parts)


def create_catalog_duckdb(manifest: list[dict], backfill: list[dict], sql: str, output_dir: Path) -> Path:
    """Create ready-to-use DuckDB file."""
    logger.info("creating_catalog_duckdb")

    db_path = output_dir / "catalog.duckdb"

    con = duckdb.connect(str(db_path))

    # Install httpfs
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")

    # Create manifest table from data
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

    for m in manifest:
        con.execute(
            "INSERT INTO manifest VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [m["date"], m["tribunal"], m["file_type"], m["table_name"],
             m["file_name"], m["ia_item"], m["ia_url"], m["created_at"]],
        )

    # Create backfill table
    con.execute("""
        CREATE TABLE backfill_needed (
            date VARCHAR,
            tribunal VARCHAR,
            reason VARCHAR,
            last_checked VARCHAR
        )
    """)

    for b in backfill:
        con.execute(
            "INSERT INTO backfill_needed VALUES (?, ?, ?, ?)",
            [b["date"], b["tribunal"], b["reason"], b["last_checked"]],
        )

    # Create helper views
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


def save_parquet(data: list[dict], output_path: Path) -> None:
    """Save data as parquet using DuckDB."""
    if not data:
        # Create empty parquet with schema
        con = duckdb.connect()
        con.execute(f"COPY (SELECT NULL as dummy WHERE FALSE) TO '{output_path}' (FORMAT PARQUET)")
        con.close()
        return

    con = duckdb.connect()

    # Create table from dict
    columns = list(data[0].keys())
    placeholders = ", ".join(["?" for _ in columns])
    col_defs = ", ".join([f"{c} VARCHAR" for c in columns])

    con.execute(f"CREATE TABLE temp ({col_defs})")

    for row in data:
        values = [row.get(c) for c in columns]
        con.execute(f"INSERT INTO temp VALUES ({placeholders})", values)

    con.execute(f"COPY temp TO '{output_path}' (FORMAT PARQUET)")
    con.close()


def upload_to_ia(files: list[Path]) -> bool:
    """Upload catalog files to Internet Archive."""
    logger.info("uploading_to_ia", files=[f.name for f in files])

    file_args = [str(f) for f in files]

    try:
        result = subprocess.run(
            ["ia", "upload", IA_CATALOG_ITEM] + file_args +
            ["--metadata=collection:opensource",
             "--metadata=mediatype:data",
             "--metadata=title:CausaGanha Catalog",
             "--metadata=description:Master catalog for CausaGanha DJEN data. Contains manifest of all files and views for remote queries.",
             "--metadata=subject:causaganha;djen;legal;brazil;catalog",
             "--metadata=creator:CausaGanha",
             "--retries=3",
             "--no-derive"],
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
    parser.add_argument("--start-date", type=str, default=None, help="Start date for backfill (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="End date for backfill (YYYY-MM-DD)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Date range for backfill calculation
    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d").date()
        if args.start_date else DJEN_START_DATE
    )
    end_date = (
        datetime.strptime(args.end_date, "%Y-%m-%d").date()
        if args.end_date else date.today() - timedelta(days=1)
    )

    print("Generating catalog...")
    print(f"  Output: {output_dir}")
    print(f"  Backfill range: {start_date} to {end_date}")
    print()

    # 1. List all IA items
    items = list_ia_items()
    print(f"Found {len(items)} items on Internet Archive")

    # 2. Generate manifest
    manifest = generate_manifest(items)
    print(f"Manifest: {len(manifest)} files indexed")

    # 3. Generate backfill list
    backfill = generate_backfill_list(manifest, start_date, end_date)
    print(f"Backfill needed: {len(backfill)} date/tribunal combinations")

    # 4. Generate SQL
    sql = generate_catalog_sql(manifest)

    # 5. Save files
    manifest_path = output_dir / "manifest.parquet"
    backfill_path = output_dir / "backfill-needed.parquet"
    sql_path = output_dir / "catalog.sql"

    save_parquet(manifest, manifest_path)
    save_parquet(backfill, backfill_path)
    sql_path.write_text(sql)

    print(f"Saved: {manifest_path}")
    print(f"Saved: {backfill_path}")
    print(f"Saved: {sql_path}")

    # 6. Create DuckDB
    db_path = create_catalog_duckdb(manifest, backfill, sql, output_dir)
    print(f"Saved: {db_path}")

    # 7. Upload if requested
    if args.upload:
        print()
        print("Uploading to Internet Archive...")
        files = [manifest_path, backfill_path, sql_path, db_path]
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

    return 0


if __name__ == "__main__":
    exit(main())
