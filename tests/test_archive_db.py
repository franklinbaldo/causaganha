# causaganha/tests/test_archive_db.py
"""
Tests for Internet Archive database integration.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import json
from pathlib import Path
from datetime import date
import sys

# Add src directory to Python path for testing
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from archive_db import DatabaseArchiver, IAConfig  # noqa: E402


class TestDatabaseArchiver(unittest.TestCase):
    """Test cases for DatabaseArchiver functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.ia_config = IAConfig(
            access_key="test_access_key", secret_key="test_secret_key"
        )

    def test_ia_config_creation(self):
        """Test IAConfig creation and validation."""
        config = IAConfig("access", "secret")
        self.assertEqual(config.access_key, "access")
        self.assertEqual(config.secret_key, "secret")

    def test_ia_config_from_env_missing_keys(self):
        """Test IAConfig.from_env with missing environment variables."""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError) as context:
                IAConfig.from_env()
            self.assertIn(
                "Missing required IA environment variables", str(context.exception)
            )

    def test_create_database_item_id(self):
        """Test Internet Archive item ID generation."""
        archiver = DatabaseArchiver(self.ia_config)

        test_date = date(2025, 6, 26)

        # Test weekly archive
        item_id = archiver.create_database_item_id(test_date, "weekly")
        self.assertEqual(item_id, "causaganha-database-2025-06-26-weekly")

        # Test monthly archive
        item_id = archiver.create_database_item_id(test_date, "monthly")
        self.assertEqual(item_id, "causaganha-database-2025-06-26-monthly")

    def test_create_archive_metadata(self):
        """Test metadata generation for Internet Archive."""
        archiver = DatabaseArchiver(self.ia_config)

        test_date = date(2025, 6, 26)
        db_stats = {
            "total_advogados": 150,
            "total_partidas": 300,
            "total_decisoes": 500,
        }

        metadata = archiver.create_archive_metadata(test_date, "weekly", db_stats)

        # Check required fields
        self.assertIn("title", metadata)
        self.assertIn("creator", metadata)
        self.assertIn("date", metadata)
        self.assertIn("description", metadata)
        self.assertIn("subject", metadata)

        # Check specific values
        self.assertEqual(metadata["creator"], "CausaGanha Project")
        self.assertEqual(metadata["date"], "2025-06-26")
        self.assertEqual(metadata["archive_type"], "weekly")

        # Check statistics are included
        self.assertIn("150", metadata["description"])
        self.assertIn("300", metadata["description"])
        self.assertIn("500", metadata["description"])

    @patch("archive_db.CausaGanhaDB")
    def test_export_database_snapshot(self, mock_db_class):
        """Test database snapshot export functionality."""
        # Mock database
        mock_db = Mock()
        mock_db.conn.execute.return_value = None
        mock_db.get_statistics.return_value = {"total_decisoes": 100}
        mock_db_class.return_value.__enter__.return_value = mock_db

        archiver = DatabaseArchiver(self.ia_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_path = temp_path / "test.duckdb"
            export_dir = temp_path / "exports"

            # Create fake database file
            db_path.write_bytes(b"fake database content")

            test_date = date(2025, 6, 26)

            # Mock pandas DataFrame for CSV exports
            with patch("pandas.DataFrame") as mock_df_class:
                mock_df = Mock()
                mock_df.to_csv = Mock()
                mock_df_class.return_value = mock_df

                # Mock the EXPORT DATABASE command to create the expected file
                def mock_execute(sql):
                    if "EXPORT DATABASE" in sql:
                        # Extract the export path from the SQL command
                        import re

                        match = re.search(r"'([^']+)'", sql)
                        if match:
                            export_path = Path(match.group(1))
                            export_path.write_bytes(b"exported database")
                        return None
                    else:
                        # For SELECT queries, return a mock with df() method
                        mock_result = Mock()
                        mock_result.df.return_value = mock_df
                        return mock_result

                mock_db.conn.execute.side_effect = mock_execute

                exports = archiver.export_database_snapshot(
                    db_path, export_dir, test_date
                )

                # Verify exports were created
                self.assertIn("database", exports)
                self.assertIn("metadata", exports)

                # Verify the metadata file exists and has correct content
                metadata_path = exports["metadata"]
                self.assertTrue(metadata_path.exists())

                with open(metadata_path, "r") as f:
                    metadata_content = json.load(f)

                self.assertEqual(metadata_content["export_date"], "2025-06-26")
                self.assertIn("export_timestamp", metadata_content)
                self.assertIn("statistics", metadata_content)

    @patch("subprocess.run")
    def test_upload_to_internet_archive_success(self, mock_subprocess):
        """Test successful upload to Internet Archive."""
        # Mock successful subprocess call
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Upload successful"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        archiver = DatabaseArchiver(self.ia_config)

        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as temp_file:
            archive_path = Path(temp_file.name)

            metadata = {
                "title": "Test Archive",
                "creator": "Test",
                "date": "2025-06-26",
            }

            result = archiver.upload_to_internet_archive(
                archive_path, "test-item-id", metadata
            )

            self.assertTrue(result)
            mock_subprocess.assert_called_once()

            # Verify the command structure
            call_args = mock_subprocess.call_args[0][0]
            self.assertEqual(call_args[0], "ia")
            self.assertEqual(call_args[1], "upload")
            self.assertEqual(call_args[2], "test-item-id")

    @patch("subprocess.run")
    def test_upload_to_internet_archive_failure(self, mock_subprocess):
        """Test failed upload to Internet Archive."""
        # Mock failed subprocess call
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Upload failed"
        mock_subprocess.return_value = mock_result

        archiver = DatabaseArchiver(self.ia_config)

        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as temp_file:
            archive_path = Path(temp_file.name)

            metadata = {"title": "Test Archive"}

            result = archiver.upload_to_internet_archive(
                archive_path, "test-item-id", metadata
            )

            self.assertFalse(result)

    def test_compress_exports(self):
        """Test compression of export files."""
        archiver = DatabaseArchiver(self.ia_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            test_file1 = temp_path / "test1.txt"
            test_file2 = temp_path / "test2.txt"
            test_file1.write_text("Test content 1")
            test_file2.write_text("Test content 2")

            exports = {"file1": test_file1, "file2": test_file2}

            archive_path = archiver.compress_exports(exports, temp_path)

            # Verify archive was created
            self.assertTrue(archive_path.exists())
            self.assertTrue(archive_path.name.endswith(".tar.gz"))
            self.assertGreater(archive_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
