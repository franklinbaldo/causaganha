MIN_ARGV_LENGTH = 2

"""Database migrations for CausaGanha.

Run migrations with: causaganha db migrate
Or directly: uv run python -m causaganha.storage.migrations
"""

import structlog
from ibis.backends.duckdb import Backend

from causaganha.storage.connection import get_connection


logger = structlog.get_logger()

MIGRATIONS = [
    # Migration 1: Add unique index on intimations.id
    {
        "version": 1,
        "name": "add_intimations_id_unique_index",
        "up": "CREATE UNIQUE INDEX IF NOT EXISTS intimations_id_unique ON intimations (id)",
        "down": "DROP INDEX IF EXISTS intimations_id_unique",
    },
    # Migration 2: Add updated_at column
    {
        "version": 2,
        "name": "add_intimations_updated_at",
        "up": "ALTER TABLE intimations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        "down": "ALTER TABLE intimations DROP COLUMN IF EXISTS updated_at",
    },
    # Migration 3: Add numeroprocessocommascara column
    {
        "version": 3,
        "name": "add_intimations_numeroprocessocommascara",
        "up": "ALTER TABLE intimations ADD COLUMN IF NOT EXISTS numeroprocessocommascara VARCHAR",
        "down": "ALTER TABLE intimations DROP COLUMN IF EXISTS numeroprocessocommascara",
    },
    # Migration 4: Add id_orgao column
    {
        "version": 4,
        "name": "add_intimations_id_orgao",
        "up": "ALTER TABLE intimations ADD COLUMN IF NOT EXISTS id_orgao INTEGER",
        "down": "ALTER TABLE intimations DROP COLUMN IF EXISTS id_orgao",
    },
    # Migration 5: Add unique index on intimation_lawyers
    {
        "version": 5,
        "name": "add_intimation_lawyers_unique_index",
        "up": "CREATE UNIQUE INDEX IF NOT EXISTS intimation_lawyers_unique ON intimation_lawyers (intimation_id, oab_number, oab_state)",
        "down": "DROP INDEX IF EXISTS intimation_lawyers_unique",
    },
    # Migration 6: Create decision_analysis view for compatibility
    {
        "version": 6,
        "name": "create_decision_analysis_view",
        "up": "CREATE OR REPLACE VIEW decision_analysis AS SELECT * FROM analysis_results",
        "down": "DROP VIEW IF EXISTS decision_analysis",
    },
    # Migration 7: Add created_at to analysis_results if missing
    {
        "version": 7,
        "name": "add_analysis_results_created_at",
        "up": "ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
        "down": "ALTER TABLE analysis_results DROP COLUMN IF EXISTS created_at",
    },
    # Migration 8: Add rated column to analysis_results if missing
    {
        "version": 8,
        "name": "add_analysis_results_rated",
        "up": "ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS rated BOOLEAN DEFAULT FALSE",
        "down": "ALTER TABLE analysis_results DROP COLUMN IF EXISTS rated",
    },
    # Migration 9: Add rated_at column to analysis_results if missing
    {
        "version": 9,
        "name": "add_analysis_results_rated_at",
        "up": "ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS rated_at TIMESTAMP",
        "down": "ALTER TABLE analysis_results DROP COLUMN IF EXISTS rated_at",
    },
    # Migration 10: Create ratings_history table
    {
        "version": 10,
        "name": "create_ratings_history",
        "up": """
            CREATE TABLE IF NOT EXISTS ratings_history (
                advogado_id VARCHAR NOT NULL,
                comunicacao_id VARCHAR NOT NULL,
                oab_number VARCHAR(20) NOT NULL,
                oab_state VARCHAR(2) NOT NULL,
                mu_before FLOAT NOT NULL,
                sigma_before FLOAT NOT NULL,
                mu_after FLOAT NOT NULL,
                sigma_after FLOAT NOT NULL,
                rating_after FLOAT NOT NULL,
                wins INTEGER NOT NULL,
                losses INTEGER NOT NULL,
                rated_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (advogado_id, comunicacao_id)
            )
        """,
        "down": "DROP TABLE IF EXISTS ratings_history",
    },
    # Migration 11: Create classificacoes table
    {
        "version": 11,
        "name": "create_classificacoes",
        "up": """
            CREATE TABLE IF NOT EXISTS classificacoes (
                texto_id VARCHAR NOT NULL,
                metodo VARCHAR(30) NOT NULL,
                outcome VARCHAR(50),
                decision_type VARCHAR(50),
                winner_advogado_id VARCHAR,
                loser_advogado_id VARCHAR,
                confidence FLOAT,
                classified_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (texto_id, metodo)
            )
        """,
        "down": "DROP TABLE IF EXISTS classificacoes",
    },
]


def ensure_migration_table(con: Backend) -> None:
    """Create migrations tracking table if it doesn't exist."""
    con.con.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)


def get_applied_migrations(con: Backend) -> set[int]:
    """Get set of applied migration versions."""
    result = con.con.execute("SELECT version FROM schema_migrations").fetchall()
    return {row[0] for row in result}


def run_migrations(con: Backend | None = None, *, dry_run: bool = False) -> list[str]:
    """Run all pending migrations.

    Args:
        con: Database connection. If None, creates new connection.
        dry_run: If True, only report what would be done.

    Returns:
        List of applied migration names.
    """
    if con is None:
        con = get_connection()

    ensure_migration_table(con)
    applied = get_applied_migrations(con)

    applied_names = []

    for migration in MIGRATIONS:
        version = migration["version"]
        name = migration["name"]

        if version in applied:
            logger.debug("migration_already_applied", version=version, name=name)
            continue

        if dry_run:
            logger.info("migration_would_apply", version=version, name=name)
            applied_names.append(name)
            continue

        logger.info("applying_migration", version=version, name=name)

        try:
            con.con.execute(migration["up"])
            con.con.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                [version, name],
            )
            logger.info("migration_applied", version=version, name=name)
            applied_names.append(name)
        except Exception as e:
            logger.exception("migration_failed", version=version, name=name, error=str(e))
            raise

    if not applied_names:
        logger.info("no_migrations_to_apply")

    return applied_names


def rollback_migration(con: Backend | None = None, target_version: int = 0) -> list[str]:
    """Rollback migrations to target version.

    Args:
        con: Database connection.
        target_version: Version to rollback to (exclusive).

    Returns:
        List of rolled back migration names.
    """
    if con is None:
        con = get_connection()

    applied = get_applied_migrations(con)
    rolled_back = []

    # Rollback in reverse order
    for migration in reversed(MIGRATIONS):
        version = migration["version"]
        name = migration["name"]

        if version not in applied or version <= target_version:
            continue

        logger.info("rolling_back_migration", version=version, name=name)

        try:
            con.con.execute(migration["down"])
            con.con.execute("DELETE FROM schema_migrations WHERE version = ?", [version])
            logger.info("migration_rolled_back", version=version, name=name)
            rolled_back.append(name)
        except Exception as e:
            logger.exception("rollback_failed", version=version, name=name, error=str(e))
            raise

    return rolled_back


def migration_status(con: Backend | None = None) -> dict:
    """Get migration status.

    Returns:
        Dict with applied, pending, and total counts.
    """
    if con is None:
        con = get_connection()

    ensure_migration_table(con)
    applied = get_applied_migrations(con)

    pending = [m for m in MIGRATIONS if m["version"] not in applied]
    applied_list = [m for m in MIGRATIONS if m["version"] in applied]

    return {
        "applied": len(applied_list),
        "pending": len(pending),
        "total": len(MIGRATIONS),
        "applied_migrations": [m["name"] for m in applied_list],
        "pending_migrations": [m["name"] for m in pending],
    }


if __name__ == "__main__":
    import sys

    con = get_connection()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "status":
            status = migration_status(con)
            if status["pending_migrations"]:
                for _name in status["pending_migrations"]:
                    pass

        elif cmd == "dry-run":
            run_migrations(con, dry_run=True)

        elif cmd == "rollback":
            target = int(sys.argv[2]) if len(sys.argv) > MIN_ARGV_LENGTH else 0
            rollback_migration(con, target)

        else:
            pass

    else:
        # Default: run migrations
        applied = run_migrations(con)

        status = migration_status(con)
