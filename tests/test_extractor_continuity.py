import unittest
from unittest.mock import patch, MagicMock
import pathlib
import os
import json
import sys
import shutil
import ibis

# Ensure the src directory is in sys.path for imports
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from extractor import GeminiExtractor

class TestExtractorContinuity(unittest.TestCase):
    def setUp(self):
        self.test_data_root = PROJECT_ROOT / "causaganha_test_data_continuity"
        self.output_json_dir = self.test_data_root / "json_output"
        self.output_json_dir.mkdir(parents=True, exist_ok=True)
        self.dummy_pdf_path = self.test_data_root / "test_continuity.pdf"

        # Create a dummy PDF file so checking exists() passes
        with open(self.dummy_pdf_path, "w") as f:
            f.write("dummy pdf content")

    def tearDown(self):
        if self.test_data_root.exists():
            shutil.rmtree(self.test_data_root)

    @patch("extractor.time.sleep") # Speed up test
    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
    @patch("extractor.genai")
    @patch.object(GeminiExtractor, "_extract_text_from_pdf")
    def test_resume_capability_duckdb(self, mock_extract, mock_genai, mock_sleep):
        # Setup mocks
        mock_genai.configure = MagicMock()
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        # Mock PDF extraction to return 2 chunks
        mock_extract.return_value = ["chunk 1 text", "chunk 2 text"]

        extractor = GeminiExtractor()

        # --- Run 1: Fail on chunk 2 ---

        response1 = MagicMock()
        response1.text = json.dumps([{"id": "1", "res": "ok"}])

        mock_model.generate_content.side_effect = [
            response1, # Chunk 1
            Exception("API Error"), Exception("API Error"), Exception("API Error"), Exception("API Error"), Exception("API Error") # Chunk 2 retries
        ]

        result_path = extractor.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)

        # Assert failure
        self.assertIsNone(result_path, "First run should fail")

        # VERIFY DUCKDB PERSISTENCE
        # Check that a DuckDB file exists
        sanitized_name = extractor._sanitize_filename(self.dummy_pdf_path.stem)
        progress_db_path = self.output_json_dir / f".{sanitized_name}_progress.duckdb"
        self.assertTrue(progress_db_path.exists(), "Progress DuckDB file should exist after failure")

        # Check content using Ibis
        con = ibis.duckdb.connect(str(progress_db_path))
        try:
            self.assertIn("progress", con.list_tables(), "Table 'progress' should exist")
            t = con.table("progress")
            rows = t.execute()
            self.assertEqual(len(rows), 1, "Should have 1 row for chunk 1")
            # Verify data
            # Assuming schema: file_name, chunk_index, decisions (as JSON string probably?)
            self.assertEqual(rows.iloc[0]["chunks_processed_count"], 1)
            # Decisions might be stored as struct or json string. Let's assume JSON string or DuckDB JSON type which maps to string in pandas usually?
            # Or map/struct.
            # I'll check column names first
            self.assertIn("decisions", rows.columns)
        finally:
            con.disconnect() # disconnect usually not needed for DuckDB in Ibis but good practice
            # Wait, con.disconnect() doesn't exist on all backends. con is just the backend.
            pass


        # --- Run 2: Resume ---

        # Reset mock
        mock_model.generate_content.reset_mock()
        mock_model.generate_content.side_effect = None

        response2 = MagicMock()
        response2.text = json.dumps([{"id": "2", "res": "ok"}])

        mock_model.generate_content.side_effect = [
            response2, # Chunk 2 (if resumed)
            response2
        ]

        result_path_2 = extractor.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)

        self.assertIsNotNone(result_path_2, "Second run should succeed")

        # CHECK: Did it resume?
        self.assertEqual(mock_model.generate_content.call_count, 1, "Should resume and only process chunk 2")

        # Check final data
        with open(result_path_2, "r") as f:
            data = json.load(f)

        decisions = data["decisions"]
        ids = [d["id"] for d in decisions]
        self.assertIn("1", ids)
        self.assertIn("2", ids)
        self.assertEqual(len(decisions), 2)

        # Check that progress file is gone
        self.assertFalse(progress_db_path.exists(), "Progress DuckDB file should be deleted after completion")

if __name__ == "__main__":
    unittest.main()
