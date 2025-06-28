import unittest
from unittest.mock import patch, MagicMock
import pathlib
import os
import json
import sys
import shutil
import fitz
import subprocess

# Ensure the src directory is in sys.path for imports
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Add scripts directory for environment checks
SCRIPTS_PATH = PROJECT_ROOT / "scripts"
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from extractor import GeminiExtractor  # noqa: E402
import check_environment  # noqa: E402

# Suppress logging output during tests for clarity, can be enabled for debugging
# logging.disable(logging.CRITICAL)


class TestGeminiExtractor(unittest.TestCase):
    def setUp(self):
        self.test_data_root = PROJECT_ROOT / "causaganha_test_data_extractor"
        self.dummy_pdf_dir = self.test_data_root / "data" / "diarios"
        self.output_json_dir = self.test_data_root / "data" / "json_extract_output"

        self.dummy_pdf_dir.mkdir(parents=True, exist_ok=True)
        self.output_json_dir.mkdir(parents=True, exist_ok=True)

        self.dummy_pdf_path = self.dummy_pdf_dir / "test_extract.pdf"
        try:
            from PyPDF2 import PdfWriter  # type: ignore

            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with open(self.dummy_pdf_path, "wb") as f:
                writer.write(f)
        except ImportError:
            with open(self.dummy_pdf_path, "wb") as f:
                f.write(
                    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
                )

    def tearDown(self):
        if self.test_data_root.exists():
            shutil.rmtree(self.test_data_root)

    def _create_pdf(self, path: pathlib.Path, pages: int) -> None:
        doc = fitz.open()
        for i in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i + 1}")
        doc.save(str(path))
        doc.close()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch.object(GeminiExtractor, "_extract_text_from_pdf")
    @patch("extractor.genai")
    def test_extract_with_api_key_and_genai_success(
        self, mock_genai, mock_extract_text_from_pdf
    ):
        mock_genai.configure = MagicMock()
        mock_extract_text_from_pdf.return_value = ["dummy text chunk for success"]
        mock_model_instance = MagicMock()
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = json.dumps(
            [
                {
                    "numero_processo": "0011223-45.2023.7.89.0000",
                    "resultado": "procedente",
                }
            ]
        )
        mock_model_instance.generate_content.return_value = mock_gemini_response
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
        mock_genai.GenerativeModel.assert_called_once_with(extractor.model_name)
        self.assertEqual(mock_model_instance.generate_content.call_count, 1)

        with open(result_path, "r") as f:
            data = json.load(f)
        self.assertIn(data["decisions"][0]["language"], {"pt", "es"})

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch.object(GeminiExtractor, "_extract_text_from_pdf")
    @patch("extractor.genai")
    def test_language_detection_translation(self, mock_genai, mock_extract_text_from_pdf):
        mock_genai.configure = MagicMock()
        mock_extract_text_from_pdf.return_value = ["dummy"]
        mock_model_instance = MagicMock()
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = json.dumps([
            {"numero_processo": "123", "resultado": "rechazado"}
        ])
        mock_model_instance.generate_content.return_value = mock_gemini_response
        mock_genai.GenerativeModel.return_value = mock_model_instance

        extractor = GeminiExtractor(enable_translation=True)
        result_path = extractor.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)
        with open(result_path, "r") as f:
            data = json.load(f)

        dec = data["decisions"][0]
        self.assertEqual(dec["language"], "es")
        self.assertNotEqual(dec.get("resultado_translated"), "rechazado")



    @patch("extractor.genai", None)
    @patch("extractor.fitz")
    def test_extract_when_genai_not_available(self, mock_fitz):
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        extractor = GeminiExtractor()
        self.assertFalse(extractor.gemini_configured)
        result_path = extractor.extract_and_save_json(
            self.dummy_pdf_path, self.output_json_dir
        )
        self.assertIsNotNone(result_path)
        with open(result_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["status"], "dummy_data_gemini_not_configured")
        mock_fitz.open.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    @patch("extractor.fitz")
    @patch("extractor.genai")
    def test_extract_when_api_key_not_available(self, mock_genai, mock_fitz):
        mock_genai.configure = MagicMock()
        extractor = GeminiExtractor(api_key=None)
        self.assertFalse(extractor.gemini_configured)
        result_path = extractor.extract_and_save_json(
            self.dummy_pdf_path, self.output_json_dir
        )
        self.assertIsNotNone(result_path)
        with open(result_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["status"], "dummy_data_gemini_not_configured")
        mock_genai.configure.assert_not_called()
        mock_fitz.open.assert_not_called()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch.object(GeminiExtractor, "_extract_text_from_pdf")
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
        mock_genai.GenerativeModel.assert_called_once_with(extractor.model_name)
        self.assertEqual(mock_model_instance.generate_content.call_count, 1)

    def test_extract_text_from_pdf_chunking(self):
        multi_pdf = self.dummy_pdf_dir / "multi_page.pdf"
        self._create_pdf(multi_pdf, 30)

        extractor = GeminiExtractor(api_key=None)
        chunks = extractor._extract_text_from_pdf(multi_pdf)

        self.assertEqual(len(chunks), 2)
        self.assertIn("PÁGINA 1", chunks[0])
        self.assertIn("PÁGINA 25", chunks[0])
        self.assertNotIn("CONTINUAÇÃO DO TRECHO", chunks[0])
        self.assertTrue(chunks[1].lstrip().startswith("=== CONTINUAÇÃO DO TRECHO ANTERIOR"))
        self.assertIn("PÁGINA 25 (OVERLAP)", chunks[1])
        self.assertIn("PÁGINA 30", chunks[1])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch("extractor.genai")
    def test_multi_page_json_parsing_success(self, mock_genai):
        multi_pdf = self.dummy_pdf_dir / "multi_parse.pdf"
        self._create_pdf(multi_pdf, 30)

        mock_genai.configure = MagicMock()
        mock_model_instance = MagicMock()
        response1 = MagicMock()
        response1.text = json.dumps([
            {"numero_processo": "111", "resultado": "procedente"}
        ])
        response2 = MagicMock()
        response2.text = json.dumps([
            {"numero_processo": "222", "resultado": "improcedente"}
        ])
        mock_model_instance.generate_content.side_effect = [response1, response2]
        mock_genai.GenerativeModel.return_value = mock_model_instance

        extractor = GeminiExtractor()
        result_path = extractor.extract_and_save_json(multi_pdf, self.output_json_dir)

        self.assertIsNotNone(result_path)
        self.assertTrue(pathlib.Path(result_path).exists())
        self.assertEqual(mock_model_instance.generate_content.call_count, 2)

        with open(result_path, "r") as f:
            data = json.load(f)

        self.assertEqual(data["chunks_processed"], 2)
        self.assertEqual(data["total_decisions_found"], 2)
        numeros = [d["numero_processo"] for d in data["decisions"]]
        self.assertEqual(numeros, ["111", "222"])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch("extractor.genai")
    def test_multi_page_json_parsing_failure(self, mock_genai):
        multi_pdf = self.dummy_pdf_dir / "multi_fail.pdf"
        self._create_pdf(multi_pdf, 30)

        mock_genai.configure = MagicMock()
        mock_model_instance = MagicMock()
        response1 = MagicMock()
        response1.text = json.dumps([
            {"numero_processo": "111", "resultado": "procedente"}
        ])
        response2 = MagicMock()
        response2.text = "not json"
        mock_model_instance.generate_content.side_effect = [response1, response2]
        mock_genai.GenerativeModel.return_value = mock_model_instance

        extractor = GeminiExtractor()
        result_path = extractor.extract_and_save_json(multi_pdf, self.output_json_dir)

        self.assertIsNone(result_path)
        self.assertEqual(mock_model_instance.generate_content.call_count, 2)
        self.assertFalse(any(self.output_json_dir.iterdir()))

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch.object(GeminiExtractor, "_extract_text_from_pdf")
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
        mock_genai.GenerativeModel.assert_called_once_with(extractor.model_name)
        self.assertEqual(mock_model_instance.generate_content.call_count, 1)


class TestCheckEnvironment(unittest.TestCase):
    @patch.object(check_environment, "sys")
    def test_check_python_version_success(self, mock_sys):
        mock_sys.version_info = (3, 11, 0)
        mock_sys.version = "3.11.0"
        self.assertTrue(check_environment.check_python_version())

    @patch.object(check_environment, "sys")
    def test_check_python_version_failure(self, mock_sys):
        mock_sys.version_info = (3, 8, 0)
        mock_sys.version = "3.8.0"
        self.assertFalse(check_environment.check_python_version())

    @patch("check_environment.Path.exists", return_value=True)
    def test_check_virtualenv_exists(self, mock_exists):
        self.assertTrue(check_environment.check_virtualenv())

    @patch("check_environment.Path.exists", return_value=False)
    def test_check_virtualenv_missing(self, mock_exists):
        self.assertFalse(check_environment.check_virtualenv())

    @patch.dict(os.environ, {"GEMINI_API_KEY": "x", "IA_ACCESS_KEY": "y", "IA_SECRET_KEY": "z"})
    def test_check_env_vars_present(self):
        self.assertTrue(check_environment.check_env_vars())

    @patch.dict(os.environ, {}, clear=True)
    def test_check_env_vars_missing(self):
        self.assertFalse(check_environment.check_env_vars())

    @patch("check_environment.subprocess.run")
    def test_run_uv_pip_check_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")
        self.assertTrue(check_environment.run_uv_pip_check())

    @patch("check_environment.subprocess.run")
    def test_run_uv_pip_check_failure(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], 1, stdout="fail", stderr="err")
        self.assertFalse(check_environment.run_uv_pip_check())

    @patch.multiple(
        check_environment,
        check_python_version=lambda: True,
        check_virtualenv=lambda: True,
        check_env_vars=lambda: True,
        run_uv_pip_check=lambda: True,
    )
    def test_main_success(self):
        self.assertEqual(check_environment.main(), 0)

    @patch.multiple(
        check_environment,
        check_python_version=lambda: True,
        check_virtualenv=lambda: False,
        check_env_vars=lambda: True,
        run_uv_pip_check=lambda: True,
    )
    def test_main_failure(self):
        self.assertEqual(check_environment.main(), 1)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)

