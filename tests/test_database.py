# causaganha/tests/test_database.py
import unittest
from pathlib import Path
import sys
import os
import tempfile

# Add src directory to Python path for testing
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from database import CausaGanhaDB # noqa: E402

class TestCausaGanhaDB(unittest.TestCase):
    """Test cases for CausaGanhaDB functionality."""

    def test_temp_db_creation_and_cleanup(self):
        """Test that a temporary database is created and cleaned up."""
        db = None
        temp_db_path_str = None
        try:
            # Instantiate without db_path to use a temporary database
            db = CausaGanhaDB()
            db.connect() # This should create and connect to the temp DB

            self.assertIsNotNone(db.conn, "Database connection should be established.")
            self.assertIsNotNone(db._temp_db_file_path, "Temporary DB file path should be set.")
            self.assertIsNone(db._temp_db_file_obj, "Temporary DB file object should be None after connect uses the path.")
            self.assertIsNotNone(db.db_path, "db_path should be set to the temporary file path.")
            self.assertEqual(db.db_path, db._temp_db_file_path, "db_path should be the same as _temp_db_file_path.")

            temp_db_path_str = str(db.db_path)
            self.assertTrue(Path(temp_db_path_str).exists(), "Temporary database file should exist on disk.")

            # Perform a simple operation to ensure migrations ran
            try:
                db.conn.execute("SELECT COUNT(*) FROM ratings").fetchone()
            except Exception as e:
                self.fail(f"Could not query 'ratings' table in temporary DB. Migrations might have failed. Error: {e}")

        finally:
            if db:
                # Store path before close, as close will None it out
                closed_temp_path_str = str(db._temp_db_file_path) if db._temp_db_file_path else None
                db.close()

            if closed_temp_path_str: # Check original path if it existed
                self.assertFalse(Path(closed_temp_path_str).exists(), "Temporary database file should be cleaned up after close.")
            if db:
                 self.assertIsNone(db._temp_db_file_path, "_temp_db_file_path should be None after close.")


    def test_persistent_db_creation(self):
        """Test that a persistent database is created when db_path is provided."""
        db = None
        # Create an empty file to simulate a scenario DuckDB needs to handle
        # CausaGanhaDB's connect method should delete this empty file before connecting.
        persistent_db_file = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
        persistent_db_path = Path(persistent_db_file.name)
        persistent_db_file.close() # Close the file handle, leaving an empty file

        try:
            db = CausaGanhaDB(db_path=persistent_db_path)
            db.connect()

            self.assertIsNotNone(db.conn, "Database connection should be established.")
            self.assertIsNone(db._temp_db_file_path, "Temporary DB file path should NOT exist for persistent DB.")
            self.assertIsNone(db._temp_db_file_obj, "Temporary DB file object should NOT exist for persistent DB.")
            self.assertEqual(db.db_path, persistent_db_path, "db_path should be the specified persistent path.")
            self.assertTrue(persistent_db_path.exists(), "Persistent database file should exist on disk.")
            self.assertGreater(persistent_db_path.stat().st_size, 0, "Persistent DB file should not be empty after migrations.")

            # Perform a simple operation
            try:
                db.conn.execute("SELECT COUNT(*) FROM ratings").fetchone()
            except Exception as e:
                self.fail(f"Could not query 'ratings' table in persistent DB. Migrations might have failed. Error: {e}")

        finally:
            if db:
                db.close()
            # Clean up the persistent test DB file
            if persistent_db_path.exists():
                persistent_db_path.unlink()
            self.assertFalse(persistent_db_path.exists(), "Persistent test database file should be cleaned up.")

    def test_db_info_with_temp_db(self):
        """Test get_db_info with a temporary database."""
        with CausaGanhaDB() as db: # Uses temporary DB
            db_info = db.get_db_info()
            # For a file-backed temporary DB, db_info["db_path"] will be the actual temp file path
            self.assertTrue(Path(db_info["db_path"]).name.startswith("tmp"), f"Expected a temp file path, got {db_info['db_path']}")
            self.assertTrue(Path(db_info["db_path"]).name.endswith(".duckdb"), f"Expected a .duckdb file, got {db_info['db_path']}")
            self.assertIsNotNone(db_info["tables"], "Table info should be present for temp DB.")
            self.assertGreaterEqual(db_info["size_bytes"], 0)


    def test_db_info_with_persistent_db(self):
        """Test get_db_info with a persistent database."""
        # Use a non-empty file that is a valid DuckDB by letting CausaGanhaDB create it
        persistent_db_file = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=True) # just to get a name
        persistent_db_path = Path(persistent_db_file.name)

        try:
            with CausaGanhaDB(db_path=persistent_db_path) as db:
                db_info = db.get_db_info()
                self.assertEqual(str(persistent_db_path), db_info["db_path"], "db_path in info should match persistent path.")
                self.assertIsNotNone(db_info["tables"], "Table info should be present for persistent DB.")
                self.assertGreater(db_info["size_bytes"], 0, "Persistent DB file size should be greater than 0.")
        finally:
            if persistent_db_path.exists():
                persistent_db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
