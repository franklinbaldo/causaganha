import unittest
from unittest.mock import patch, MagicMock
import pathlib
import os
import json
import sys
import shutil
import logging  # Added import

# Ensure the src directory is in sys.path for imports
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from extractor import GeminiExtractor  # noqa: E402

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
        # Create a real (but tiny) PDF for fitz to open without error
        try:
            from PyPDF2 import (
                PdfWriter,
            )  # PyPDF2 is usually a dev dependency or part of a larger PDF handling suite

            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with open(self.dummy_pdf_path, "wb") as f:
                writer.write(f)
        except (
            ImportError
        ):  # Fallback if PyPDF2 is not available in the test env for some reason
            with open(self.dummy_pdf_path, "wb") as f:
                f.write(
                    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
                )

    def tearDown(self):
        if self.test_data_root.exists():
            shutil.rmtree(self.test_data_root)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch.object(GeminiExtractor, "_extract_text_from_pdf")  # Mock a nível de método
    @patch("extractor.genai")
    def test_extract_with_api_key_and_genai_success(
        self, mock_genai, mock_extract_text_from_pdf
    ):
        # Configure mock_genai
        mock_genai.configure = MagicMock()

        # Mock _extract_text_from_pdf para retornar um chunk
        mock_extract_text_from_pdf.return_value = ["dummy text chunk for success"]

        mock_model_instance = MagicMock()
        mock_gemini_response = MagicMock()
        # Gemini returns a LIST of decisions
        mock_gemini_response.text = json.dumps(
            [
                {
                    "numero_processo": "0011223-45.2023.7.89.0000",
                    "tipo_decisao": "sentença",
                    "polo_ativo": ["Teste Requerente"],
                    "advogados_polo_ativo": ["Adv Teste (OAB/UF 987)"],
                    "polo_passivo": ["Teste Requerido"],
                    "advogados_polo_passivo": ["Adv Teste2 (OAB/UF 654)"],
                    "resultado": "procedente",
                    "data": "2023-10-26",
                    "resumo": "Resumo da decisão.",
                }
            ]
        )
        mock_model_instance.generate_content.return_value = mock_gemini_response
        # Model name from extractor.py
        mock_genai.GenerativeModel.return_value = mock_model_instance

        extractor = GeminiExtractor()
        self.assertTrue(extractor.gemini_configured)

        result_path = extractor.extract_and_save_json(
            self.dummy_pdf_path, self.output_json_dir
        )

        self.assertIsNotNone(result_path)
        self.assertTrue(pathlib.Path(result_path).exists())

        mock_genai.configure.assert_called_once_with(api_key="fake_key_for_test")
        mock_extract_text_from_pdf.assert_called_once_with(self.dummy_pdf_path)

        mock_genai.GenerativeModel.assert_called_once_with(
            "gemini-2.5-flash-lite-preview-06-17"
        )
        self.assertEqual(mock_model_instance.generate_content.call_count, 1)

        with open(result_path, "r") as f:
            data = json.load(f)

        self.assertIn("file_name_source", data)
        self.assertEqual(data["file_name_source"], self.dummy_pdf_path.name)
        self.assertIn("decisions", data)
        self.assertIsInstance(data["decisions"], list)
        self.assertEqual(len(data["decisions"]), 1)
        self.assertEqual(data["chunks_processed"], 1)
        self.assertEqual(data["total_decisions_found"], 1)

        decision_one = data["decisions"][0]
        self.assertEqual(decision_one["numero_processo"], "0011223-45.2023.7.89.0000")
        self.assertEqual(decision_one["tipo_decisao"], "sentença")
        self.assertEqual(decision_one["polo_ativo"], ["Teste Requerente"])
        self.assertEqual(
            decision_one["advogados_polo_ativo"], ["Adv Teste (OAB/UF 987)"]
        )
        self.assertEqual(decision_one["resultado"], "procedente")
        self.assertEqual(decision_one["data"], "2023-10-26")

    @patch("extractor.genai", None)
    @patch("extractor.fitz")  # Still mock fitz as it's tried before genai check
    def test_extract_when_genai_not_available(self, mock_fitz):
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        extractor = GeminiExtractor()
        self.assertFalse(extractor.gemini_configured)

        result_path = extractor.extract_and_save_json(
            self.dummy_pdf_path, self.output_json_dir
        )
        self.assertIsNotNone(result_path)
        self.assertTrue(pathlib.Path(result_path).exists())
        with open(result_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["status"], "dummy_data_gemini_not_configured")
        mock_fitz.open.assert_not_called()  # fitz shouldn't be called if genai is not configured for real calls

    @patch.dict(os.environ, {}, clear=True)
    @patch("extractor.fitz")  # Mock fitz
    @patch("extractor.genai")  # Mock genai
    def test_extract_when_api_key_not_available(self, mock_genai, mock_fitz):
        mock_genai.configure = MagicMock()  # genai is importable but will fail config

        extractor = GeminiExtractor(api_key=None)
        self.assertFalse(extractor.gemini_configured)

        result_path = extractor.extract_and_save_json(
            self.dummy_pdf_path, self.output_json_dir
        )
        self.assertIsNotNone(result_path)
        self.assertTrue(pathlib.Path(result_path).exists())
        with open(result_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["status"], "dummy_data_gemini_not_configured")
        mock_genai.configure.assert_not_called()
        mock_fitz.open.assert_not_called()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch.object(GeminiExtractor, "_extract_text_from_pdf")  # Mock a nível de método
    @patch("extractor.genai")
    def test_api_call_failure_generate_content(
        self, mock_genai, mock_extract_text_from_pdf
    ):
        mock_genai.configure = MagicMock()
        mock_extract_text_from_pdf.return_value = ["dummy text chunk for api failure"]

        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.side_effect = Exception("Gemini API Error")
        mock_genai.GenerativeModel.return_value = mock_model_instance

        extractor = GeminiExtractor()
        self.assertTrue(extractor.gemini_configured)

        result_path = extractor.extract_and_save_json(
            self.dummy_pdf_path, self.output_json_dir
        )
        self.assertIsNone(result_path)
        mock_extract_text_from_pdf.assert_called_once_with(self.dummy_pdf_path)
        mock_genai.GenerativeModel.assert_called_once_with(
            "gemini-2.5-flash-lite-preview-06-17"
        )
        self.assertEqual(mock_model_instance.generate_content.call_count, 1)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch.object(GeminiExtractor, "_extract_text_from_pdf")  # Mock a nível de método
    @patch("extractor.genai")
    def test_json_parsing_failure(self, mock_genai, mock_extract_text_from_pdf):
        mock_genai.configure = MagicMock()
        mock_extract_text_from_pdf.return_value = ["dummy text chunk for json failure"]

        mock_model_instance = MagicMock()
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = "This is not valid JSON { definitely not"
        mock_model_instance.generate_content.return_value = mock_gemini_response
        mock_genai.GenerativeModel.return_value = mock_model_instance

        extractor = GeminiExtractor()
        self.assertTrue(extractor.gemini_configured)

        result_path = extractor.extract_and_save_json(
            self.dummy_pdf_path, self.output_json_dir
        )
        self.assertIsNone(result_path)
        mock_extract_text_from_pdf.assert_called_once_with(self.dummy_pdf_path)
        mock_genai.GenerativeModel.assert_called_once_with(
            "gemini-2.5-flash-lite-preview-06-17"
        )
        self.assertEqual(mock_model_instance.generate_content.call_count, 1)


if __name__ == "__main__":
    # PyPDF2 availability check removed - not used in tests
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
