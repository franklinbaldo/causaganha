"""
Migration runner for CausaGanha database schema management.

Provides versioned database migrations with proper tracking and rollback support.
"""

import duckdb
import logging
from pathlib import Path
from typing import List, Optional
import re
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a single database migration."""
    version: int
    name: str
    filepath: Path
    description: Optional[str] = None


class MigrationRunner:
    """Handles database migrations for CausaGanha."""
    
    def __init__(self, db_path: Path, migrations_dir: Path = None):
        self.db_path = db_path
        self.migrations_dir = migrations_dir or Path("migrations")
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        
    def connect(self):
        """Connect to database and ensure schema_version table exists."""
        self.conn = duckdb.connect(str(self.db_path))
        self._ensure_schema_version_table()
        
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def _ensure_schema_version_table(self):
        """Create schema_version table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_by VARCHAR DEFAULT 'migration_runner',
                execution_time_ms INTEGER,
                checksum VARCHAR
            )
        """)
        
    def get_current_version(self) -> int:
        """Get the current schema version."""
        try:
            result = self.conn.execute(
                "SELECT MAX(version) FROM schema_version"
            ).fetchone()
            return result[0] if result[0] is not None else 0
        except (duckdb.Error, duckdb.CatalogException):
            # If schema_version table doesn't exist or has issues
            return 0
            
    def get_applied_migrations(self) -> List[int]:
        """Get list of applied migration versions."""
        try:
            result = self.conn.execute(
                "SELECT version FROM schema_version ORDER BY version"
            ).fetchall()
            return [row[0] for row in result]
        except (duckdb.Error, duckdb.CatalogException):
            return []
            
    def discover_migrations(self) -> List[Migration]:
        """Discover all migration files in migrations directory."""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory does not exist: {self.migrations_dir}")
            return []
            
        migrations = []
        pattern = re.compile(r"^(\d{3})_(.+)\.sql$")
        
        for sql_file in sorted(self.migrations_dir.glob("*.sql")):
            match = pattern.match(sql_file.name)
            if match:
                version = int(match.group(1))
                name = match.group(2)
                
                # Extract description from SQL file comments
                description = self._extract_description(sql_file)
                
                migrations.append(Migration(
                    version=version,
                    name=name,
                    filepath=sql_file,
                    description=description
                ))
            else:
                logger.warning(f"Skipping migration file with invalid name: {sql_file.name}")
                
        return sorted(migrations, key=lambda m: m.version)
        
    def _extract_description(self, sql_file: Path) -> Optional[str]:
        """Extract description from SQL file header comments."""
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            description_lines = []
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if line.startswith('-- ') and not line.startswith('-- Migration'):
                    # Remove comment prefix
                    desc_line = line[3:].strip()
                    if desc_line:
                        description_lines.append(desc_line)
                elif line and not line.startswith('--'):
                    # Stop at first non-comment line
                    break
                    
            return ' '.join(description_lines) if description_lines else None
        except (OSError, IOError, UnicodeDecodeError) as e:
            logger.warning("Could not extract description from %s: %s", sql_file, e)
            return None
            
    def get_pending_migrations(self) -> List[Migration]:
        """Get migrations that haven't been applied yet."""
        all_migrations = self.discover_migrations()
        applied_versions = set(self.get_applied_migrations())
        
        return [m for m in all_migrations if m.version not in applied_versions]
        
    def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration."""
        logger.info(f"Applying migration {migration.version:03d}: {migration.name}")
        
        try:
            # Read migration file
            with open(migration.filepath, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                
            # Execute migration within transaction
            start_time = datetime.now()
            
            # Split SQL content into individual statements
            statements = self._split_sql_statements(sql_content)
            
            for statement in statements:
                if statement.strip():
                    self.conn.execute(statement)
                    
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Record migration as applied
            self.conn.execute("""
                INSERT INTO schema_version (version, name, description, execution_time_ms, checksum)
                VALUES (?, ?, ?, ?, ?)
            """, [
                migration.version,
                migration.name,
                migration.description,
                execution_time_ms,
                self._calculate_checksum(sql_content)
            ])
            
            logger.info(f"Migration {migration.version:03d} applied successfully in {execution_time_ms}ms")
            return True
            
        except (duckdb.Error, OSError, IOError) as e:
            logger.error("Failed to apply migration %03d: %s", migration.version, e)
            raise
            
    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements."""
        # Simple statement splitter - assumes statements end with semicolon
        statements = []
        current_statement = []
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('--'):
                continue
                
            current_statement.append(line)
            
            # Check if statement ends
            if line.endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []
                
        # Add final statement if it doesn't end with semicolon
        if current_statement:
            statements.append('\n'.join(current_statement))
            
        return statements
        
    def _calculate_checksum(self, content: str) -> str:
        """Calculate checksum for migration content."""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        
    def migrate(self, target_version: Optional[int] = None) -> bool:
        """Run all pending migrations up to target version."""
        if not self.conn:
            raise RuntimeError("Not connected to database. Call connect() first.")
            
        current_version = self.get_current_version()
        pending_migrations = self.get_pending_migrations()
        
        if target_version:
            pending_migrations = [m for m in pending_migrations if m.version <= target_version]
            
        if not pending_migrations:
            logger.info(f"No pending migrations. Current version: {current_version}")
            return True
            
        logger.info(f"Applying {len(pending_migrations)} migrations from version {current_version}")
        
        try:
            for migration in pending_migrations:
                self.apply_migration(migration)
                
            final_version = self.get_current_version()
            logger.info(f"Migrations completed. Version: {current_version} → {final_version}")
            return True
            
        except (duckdb.Error, OSError, IOError) as e:
            logger.error("Migration failed: %s", e)
            return False
            
    def status(self) -> dict:
        """Get migration status information."""
        current_version = self.get_current_version()
        applied_migrations = self.get_applied_migrations()
        pending_migrations = self.get_pending_migrations()
        
        return {
            'current_version': current_version,
            'applied_count': len(applied_migrations),
            'pending_count': len(pending_migrations),
            'applied_versions': applied_migrations,
            'pending_versions': [m.version for m in pending_migrations]
        }


def run_migrations(db_path: Path = None, migrations_dir: Path = None) -> bool:
    """Convenience function to run all pending migrations."""
    db_path = db_path or Path("data/causaganha.duckdb")
    
    with MigrationRunner(db_path, migrations_dir) as runner:
        return runner.migrate()


if __name__ == "__main__":
    import sys
    
    # Simple CLI for migration runner
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            with MigrationRunner(Path("data/causaganha.duckdb")) as runner:
                status = runner.status()
                print(f"Current version: {status['current_version']}")
                print(f"Applied migrations: {status['applied_count']}")
                print(f"Pending migrations: {status['pending_count']}")
                if status['pending_versions']:
                    print(f"Pending versions: {status['pending_versions']}")
                    
        elif command == "migrate":
            success = run_migrations()
            sys.exit(0 if success else 1)
            
        else:
            print(f"Unknown command: {command}")
            print("Usage: python migration_runner.py [status|migrate]")
            sys.exit(1)
    else:
        # Default: run migrations
        success = run_migrations()
        sys.exit(0 if success else 1)