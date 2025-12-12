import duckdb
import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self, db_path: Path, migrations_dir: Path):
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        self.conn = None

    def __enter__(self):
        # Ensure directory exists
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.conn = duckdb.connect(str(self.db_path))
        except Exception as e:
            logger.error(f"Failed to connect to DB at {self.db_path}: {e}")
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def _ensure_schema_version_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_by TEXT DEFAULT 'migration_runner',
                execution_time_ms INTEGER,
                checksum TEXT
            )
        """)

    def _get_applied_versions(self) -> List[int]:
        self._ensure_schema_version_table()
        try:
            return [row[0] for row in self.conn.execute("SELECT version FROM schema_version ORDER BY version").fetchall()]
        except duckdb.Error as e:
            logger.error(f"Error fetching applied versions: {e}")
            return []

    def _get_migration_files(self) -> List[Path]:
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return []

        files = list(self.migrations_dir.glob("*.sql"))

        migration_files = []
        for f in files:
            match = re.match(r"^(\d+)_", f.name)
            if match:
                migration_files.append((int(match.group(1)), f))

        migration_files.sort(key=lambda x: x[0])
        return [f for _, f in migration_files]

    def migrate(self) -> bool:
        if not self.conn:
             raise RuntimeError("MigrationRunner used outside context manager or not connected.")

        logger.info(f"Checking for migrations in {self.migrations_dir}")
        applied_versions = self._get_applied_versions()
        logger.info(f"Applied versions: {applied_versions}")

        migration_files = self._get_migration_files()

        success = True
        for file_path in migration_files:
            try:
                match = re.match(r"^(\d+)_", file_path.name)
                if not match:
                    continue
                version = int(match.group(1))
            except ValueError:
                continue

            if version in applied_versions:
                continue

            logger.info(f"Applying migration {version}: {file_path.name}")
            try:
                sql_content = file_path.read_text()
                checksum = hashlib.md5(sql_content.encode('utf-8')).hexdigest()

                start_time = datetime.now()
                self.conn.execute("BEGIN TRANSACTION")
                try:
                    self.conn.execute(sql_content)
                    end_time = datetime.now()
                    duration_ms = int((end_time - start_time).total_seconds() * 1000)

                    description = f"Applied migration {file_path.name}"

                    self.conn.execute("""
                        INSERT INTO schema_version (version, name, description, applied_by, execution_time_ms, checksum)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, [version, file_path.name, description, 'migration_runner', duration_ms, checksum])

                    self.conn.execute("COMMIT")
                    logger.info(f"Successfully applied migration {version}")
                except Exception as e:
                    self.conn.execute("ROLLBACK")
                    logger.error(f"Failed to apply migration {version}: {e}")
                    success = False
                    break
            except Exception as e:
                logger.error(f"Error reading migration file {file_path}: {e}")
                success = False
                break

        return success
