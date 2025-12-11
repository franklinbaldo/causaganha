import unittest
from unittest.mock import patch, MagicMock
import pathlib
import os
import json
import sys
import shutil

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
    def test_resume_capability(self, mock_extract, mock_genai, mock_sleep):
        # Setup mocks
        mock_genai.configure = MagicMock()
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        # Mock PDF extraction to return 2 chunks
        mock_extract.return_value = ["chunk 1 text", "chunk 2 text"]

        extractor = GeminiExtractor()

        # --- Run 1: Fail on chunk 2 ---

        # Response for chunk 1 (success)
        response1 = MagicMock()
        response1.text = json.dumps([{"id": "1", "res": "ok"}])

        # Response for chunk 2 (failure - returns invalid json or raises error)
        # In the code, if generate_content raises, it retries. If it returns invalid JSON, it logs error and continues?
        # Let's see code:
        # catch Exception as e_api -> retry loop.
        # if max retries -> response_successful = False -> return None.
        # So we simulate max retries failure by raising Exception every time.

        mock_model.generate_content.side_effect = [
            response1, # Chunk 1
            Exception("API Error"), Exception("API Error"), Exception("API Error"), Exception("API Error"), Exception("API Error") # Chunk 2 retries
        ]

        result_path = extractor.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)

        # Assert failure
        self.assertIsNone(result_path, "First run should fail")

        # Verify call count (1 success + 5 retries = 6 calls)
        # Or simply that it tried chunk 1 and chunk 2
        # We can inspect print/logs, but mocking side_effect is enough to know it went through.

        # --- Run 2: Resume ---

        # Reset mock
        mock_model.generate_content.reset_mock()
        mock_model.generate_content.side_effect = None

        # Setup success for both chunks (but we expect only chunk 2 to be called)
        response2 = MagicMock()
        response2.text = json.dumps([{"id": "2", "res": "ok"}])

        # If it DOESN'T resume, it will ask for chunk 1 again, then chunk 2.
        # If it DOES resume, it will only ask for chunk 2.
        # We provide responses for both scenarios just in case, to see what happens.
        mock_model.generate_content.side_effect = [
            response2, # Chunk 2 (if resumed) OR Chunk 1 (if not resumed)
            response2  # Chunk 2 (if not resumed)
        ]

        result_path_2 = extractor.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)

        # In RED phase, this might succeed if we provide enough responses,
        # but the assertion on call_count will fail.

        self.assertIsNotNone(result_path_2, "Second run should succeed")

        # CHECK: Did it resume?
        # If resumed, call_count should be 1 (only chunk 2).
        # If not resumed, call_count should be 2 (chunk 1 + chunk 2).
        self.assertEqual(mock_model.generate_content.call_count, 1, "Should resume and only process chunk 2")

        # Check final data
        with open(result_path_2, "r") as f:
            data = json.load(f)

        decisions = data["decisions"]
        # If resumed correctly, we should have id 1 (from progress) and id 2 (from run 2)
        ids = [d["id"] for d in decisions]
        self.assertIn("1", ids)
        self.assertIn("2", ids)
        self.assertEqual(len(decisions), 2)

        # Check that progress file is gone
        progress_file = self.output_json_dir / f".{self.dummy_pdf_path.stem}_extraction_progress.json"
        self.assertFalse(progress_file.exists(), "Progress file should be deleted after completion")

if __name__ == "__main__":
    unittest.main()
