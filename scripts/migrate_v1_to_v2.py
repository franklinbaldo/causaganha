#!/usr/bin/env python3
"""Migration script from CausaGanha V1 (DuckDB) to V2 (DuckDB/Ibis).

This script migrates lawyer ratings from V1 to V2.
It assumes V1 uses DuckDB and lawyer IDs are strings in format "Name (OAB/UF Number)".
"""

import re
import sys
from pathlib import Path

import duckdb
import structlog


# Ensure src is in pythonpath
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.config import DB_PATH as V2_DB_PATH
from causaganha.storage.connection import get_connection


logger = structlog.get_logger()

def parse_v1_lawyer_id(lawyer_id: str) -> tuple[str | None, str | None, str | None]:
    """Parses V1 lawyer ID string to extract Name, OAB, State.
    Expected format: "NAME (OAB/UF NUMBER)" or similar.
    Returns: (Name, OAB Number, OAB State).
    """
    # Regex for "Name (OAB/UF 12345)" or "Name (OAB/UF 12345A)"
    # Handles cases with/without space after OAB/
    pattern = r"(.*?)\s*\(OAB/([A-Z]{2})\s*([\d\w]+)\)"
    match = re.search(pattern, lawyer_id)

    if match:
        name = match.group(1).strip()
        state = match.group(2)
        number = match.group(3)
        return name, number, state

    return None, None, None

def migrate_ratings(v1_path: str, v2_con) -> None:
    """Migrate ratings from V1 to V2."""
    logger.info("Migrating ratings from V1", v1_path=v1_path)

    try:
        v1_con = duckdb.connect(v1_path, read_only=True)

        # Check if ratings table exists
        tables = [t[0] for t in v1_con.execute("SHOW TABLES").fetchall()]
        if "ratings" not in tables:
            logger.warning("V1 'ratings' table not found. Skipping ratings migration.")
            return

        # Fetch all ratings
        ratings = v1_con.execute("SELECT advogado_id, mu, sigma, total_partidas FROM ratings").fetchall()
        logger.info(f"Found {len(ratings)} ratings in V1")

        migrated_count = 0
        skipped_count = 0

        for r in ratings:
            adv_id, mu, sigma, total_partidas = r

            name, oab, state = parse_v1_lawyer_id(adv_id)

            if name and oab and state:
                # Insert into V2 lawyer_ratings
                try:
                    # Using backend.con for parameterized query to handle escaping and NULLs safely
                    # Note: We assume v2_con is an Ibis backend wrapping a DuckDB connection
                    if hasattr(v2_con, "con"):
                        con = v2_con.con
                    else:
                        # Fallback or direct DuckDB connection
                        con = v2_con

                    con.execute("""
                        INSERT INTO lawyer_ratings (
                            oab_number, oab_state, lawyer_name,
                            mu, sigma, total_cases, last_updated
                        ) VALUES (
                            ?, ?, ?,
                            ?, ?, ?, now()
                        )
                        ON CONFLICT (oab_number, oab_state) DO UPDATE SET
                            mu = EXCLUDED.mu,
                            sigma = EXCLUDED.sigma,
                            total_cases = EXCLUDED.total_cases,
                            lawyer_name = EXCLUDED.lawyer_name,
                            last_updated = now()
                    """, [oab, state, name, mu, sigma, total_partidas])

                    migrated_count += 1
                except Exception as e:
                    logger.exception("Failed to insert rating", adv_id=adv_id, error=str(e))
                    skipped_count += 1
            else:
                logger.warning("Could not parse lawyer ID", adv_id=adv_id)
                skipped_count += 1

        logger.info("Ratings migration complete", migrated=migrated_count, skipped=skipped_count)

    except Exception as e:
        logger.exception("Migration failed", error=str(e))
    finally:
        if "v1_con" in locals():
            v1_con.close()

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Migrate CausaGanha V1 data to V2")
    parser.add_argument("v1_db_path", help="Path to V1 DuckDB file")
    args = parser.parse_args()

    v1_path = args.v1_db_path
    if not Path(v1_path).exists():
        logger.error(f"V1 database file not found: {v1_path}")
        sys.exit(1)

    # Connect to V2 DB
    v2_con = get_connection(V2_DB_PATH)

    migrate_ratings(v1_path, v2_con)

    logger.info("Migration script finished")

if __name__ == "__main__":
    main()
