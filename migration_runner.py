import duckdb
from pathlib import Path


class MigrationRunner:
    """
    Stub MigrationRunner to support database migrations.

    This class is intended to be patched in tests. For real migrations, implement
    the migrate() method accordingly.
    """

    def __init__(self, db_path: Path, migrations_dir: Path):
        self.db_path = db_path
        self.migrations_dir = migrations_dir

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def migrate(self) -> bool:
        # Default stub: no-op successful migration
        return True
