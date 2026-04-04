#!/usr/bin/env python3
"""Export lawyer ratings from DuckDB catalog to Parquet on Internet Archive.

This script reads the `lawyer_ratings` and `ratings_history` tables from
the local DuckDB catalog and uploads them as Parquet files to the
`causaganha-catalog` item on Internet Archive.

Usage:
    python scripts/pipeline/export_ratings.py
    python scripts/pipeline/export_ratings.py --dry-run
    python scripts/pipeline/export_ratings.py --db catalog/catalog.duckdb
"""

import argparse
import sys
import tempfile
from pathlib import Path

import duckdb
import httpx
import structlog

from scripts.pipeline.ia_s3 import get_ia_s3_auth, upload_to_ia


logger = structlog.get_logger()

CATALOG_ITEM = "causaganha-catalog"
TABLES = ["lawyer_ratings", "ratings_history"]


def export_ratings(
    db_path: str = "catalog/catalog.duckdb",
    *,
    dry_run: bool = False,
) -> dict[str, int]:
    """Export rating tables to Parquet and upload to IA.

    Returns dict of table_name -> row_count for exported tables.
    """
    stats: dict[str, int] = {}

    if not Path(db_path).exists():
        logger.warning("catalog_not_found", path=db_path)
        return stats

    con = duckdb.connect(db_path, read_only=True)

    # Check which tables exist
    existing = {row[0] for row in con.execute("SHOW TABLES").fetchall()}

    ia_auth = get_ia_s3_auth()
    upload_headers = {"Authorization": ia_auth} if ia_auth else {}
    if not ia_auth and not dry_run:
        logger.warning("ia_credentials_not_found")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        with httpx.Client(timeout=300, headers=upload_headers) as client:
            for table in TABLES:
                if table not in existing:
                    logger.info("table_not_found", table=table)
                    continue

                count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                if count == 0:
                    logger.info("table_empty", table=table)
                    continue

                output_path = tmp_path / f"{table}.parquet"
                con.execute(f"COPY {table} TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
                size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(
                    "parquet_created",
                    table=table,
                    rows=count,
                    size_mb=f"{size_mb:.1f}",
                )

                if not dry_run and ia_auth:
                    success = upload_to_ia(client, CATALOG_ITEM, output_path, "ratings")
                    if success:
                        logger.info("uploaded", table=table)
                    else:
                        logger.error("upload_failed", table=table)

                stats[table] = count

    con.close()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Export lawyer ratings to Parquet on IA")
    parser.add_argument(
        "--db",
        default="catalog/catalog.duckdb",
        help="Path to DuckDB catalog database",
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't upload to IA")
    args = parser.parse_args()

    stats = export_ratings(args.db, dry_run=args.dry_run)

    if stats:
        logger.info("export_complete", tables=stats)
    else:
        logger.info("nothing_to_export")

    return 0


if __name__ == "__main__":
    sys.exit(main())
