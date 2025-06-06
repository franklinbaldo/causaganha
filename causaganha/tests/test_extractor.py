import unittest
from unittest.mock import patch, MagicMock, mock_open
import pathlib
import os
import json
import sys
import shutil
import logging # Added import

# Ensure the project root is in sys.path for imports
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from causaganha.core.extractor import GeminiExtractor

# Suppress logging output during tests
logging.disable(logging.CRITICAL)

class TestGeminiExtractor(unittest.TestCase):
    def setUp(self):
        self.test_data_root = PROJECT_ROOT / "causaganha_test_data_extractor"
        self.dummy_pdf_dir = self.test_data_root / "data" / "diarios"
        self.output_json_dir = self.test_data_root / "data" / "json_extract_output"

        self.dummy_pdf_dir.mkdir(parents=True, exist_ok=True)
        self.output_json_dir.mkdir(parents=True, exist_ok=True)

        self.dummy_pdf_path = self.dummy_pdf_dir / "test_extract.pdf"
        with open(self.dummy_pdf_path, "wb") as f:
            f.write(b"dummy PDF content") # Minimal content

    def tearDown(self):
        if self.test_data_root.exists():
            shutil.rmtree(self.test_data_root)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch('causaganha.core.extractor.genai')
    def test_extract_with_api_key_and_genai_success(self, mock_genai):
        # Configure mock_genai
        mock_genai.configure = MagicMock()

        mock_uploaded_file = MagicMock()
        mock_uploaded_file.name = "uploaded_files/test_extract_pdf_id"
        mock_genai.upload_file.return_value = mock_uploaded_file

        mock_model_instance = MagicMock()
        mock_gemini_response = MagicMock()
        # This is the critical part: what Gemini returns
        mock_gemini_response.text = json.dumps({
            "numero_processo": "0011223-45.2023.7.89.0000",
            "tipo_decisao": "sentença",
            "partes": {"requerente": ["Teste Requerente"], "requerido": ["Teste Requerido"]},
            "advogados": {"requerente": ["Adv Teste (OAB/UF 987)"], "requerido": ["Adv Teste2 (OAB/UF 654)"]},
            "resultado": "procedente",
            "data_decisao": "2023-10-26"
        })
        mock_model_instance.generate_content.return_value = mock_gemini_response
        mock_genai.GenerativeModel.return_value = mock_model_instance

        mock_genai.delete_file = MagicMock()

        extractor = GeminiExtractor() # Will pick up fake_key_for_test
        self.assertTrue(extractor.gemini_configured) # Check if configuration was attempted and deemed successful

        result_path = extractor.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)

        self.assertIsNotNone(result_path)
        self.assertTrue(pathlib.Path(result_path).exists())

        mock_genai.configure.assert_called_once_with(api_key="fake_key_for_test")
        mock_genai.upload_file.assert_called_once_with(
            path=str(self.dummy_pdf_path), mime_type="application/pdf"
        )
        mock_genai.GenerativeModel.assert_called_once_with('gemini-1.5-flash')
        # Check that generate_content was called (args are complex, check it was called)
        self.assertTrue(mock_model_instance.generate_content.called)
        mock_genai.delete_file.assert_called_once_with(mock_uploaded_file.name)

        with open(result_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data["numero_processo"], "0011223-45.2023.7.89.0000")
        self.assertIn("file_name_source", data)
        self.assertEqual(data["file_name_source"], self.dummy_pdf_path.name)

    @patch('causaganha.core.extractor.genai', None) # Simulate genai not being importable
    def test_extract_when_genai_not_available(self):
        # Ensure GEMINI_API_KEY is not a factor if genai is None
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        extractor = GeminiExtractor() # api_key will be None, genai is None
        self.assertFalse(extractor.gemini_configured)

        result_path = extractor.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)
        self.assertIsNotNone(result_path) # Should create dummy JSON
        self.assertTrue(pathlib.Path(result_path).exists())
        with open(result_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data["status"], "dummy_data_gemini_not_configured")

    @patch('causaganha.core.extractor.genai') # genai is importable (mocked)
    @patch.dict(os.environ, {}, clear=True) # Clear API key from environ
    def test_extract_when_api_key_not_available(self, mock_genai_module):
        # Mock genai.configure to avoid real configuration attempt if it was missed
        mock_genai_module.configure = MagicMock()

        extractor = GeminiExtractor(api_key=None) # Explicitly pass no key
        self.assertFalse(extractor.gemini_configured)

        result_path = extractor.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)
        self.assertIsNotNone(result_path) # Should create dummy JSON
        self.assertTrue(pathlib.Path(result_path).exists())
        with open(result_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data["status"], "dummy_data_gemini_not_configured")
        mock_genai_module.configure.assert_not_called() # Should not be called if API key is missing

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch('causaganha.core.extractor.genai')
    def test_api_call_failure_generate_content(self, mock_genai):
        mock_genai.configure = MagicMock()
        mock_uploaded_file = MagicMock(name="uploaded_files/test_id")
        mock_genai.upload_file.return_value = mock_uploaded_file

        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.side_effect = Exception("Gemini API Error")
        mock_genai.GenerativeModel.return_value = mock_model_instance
        mock_genai.delete_file = MagicMock()

        extractor = GeminiExtractor()
        self.assertTrue(extractor.gemini_configured)

        result_path = extractor.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)
        self.assertIsNone(result_path) # Should return None on API error
        mock_genai.delete_file.assert_called_once_with(mock_uploaded_file.name) # File should still be deleted

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch('causaganha.core.extractor.genai')
    def test_json_parsing_failure(self, mock_genai):
        mock_genai.configure = MagicMock()
        mock_uploaded_file = MagicMock(name="uploaded_files/test_id")
        mock_genai.upload_file.return_value = mock_uploaded_file

        mock_model_instance = MagicMock()
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = "This is not valid JSON { definitely not"
        mock_model_instance.generate_content.return_value = mock_gemini_response
        mock_genai.GenerativeModel.return_value = mock_model_instance
        mock_genai.delete_file = MagicMock()

        extractor = GeminiExtractor()
        self.assertTrue(extractor.gemini_configured)

        result_path = extractor.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)
        self.assertIsNone(result_path) # Should return None on JSON parsing error
        mock_genai.delete_file.assert_called_once_with(mock_uploaded_file.name)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
