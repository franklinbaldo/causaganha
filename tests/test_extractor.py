import unittest
import pathlib
import os
import json
import sys
import fitz
from unittest import mock
from unittest.mock import patch, MagicMock


# Attempt to import the class to be tested
try:
    from src.extractor import GeminiExtractor
except ImportError:
    # This is a fallback for environments where src. is not in the python path directly
    # This might happen in some CI/CD setups or when running tests from a different working directory
    import sys
    # Assuming the tests directory is a sibling of the src directory
    # Adjust the path as necessary for your project structure
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    from src.extractor import GeminiExtractor


# Helper function to create a dummy PDF file for testing
def create_dummy_pdf(path, num_pages=1):
    try:
        from PyPDF2 import PdfWriter

        writer = PdfWriter()
        for _ in range(num_pages):
            writer.add_blank_page(width=612, height=792)  # Standard letter size
        with open(path, "wb") as f:
            writer.write(f)
        return True
    except Exception:
        pass

    try:
        import fitz

        doc = fitz.open()
        for _ in range(num_pages):
            doc.new_page()
        doc.save(str(path))
        doc.close()
        return True
    except Exception:
        with open(path, "w") as f:
            f.write("Dummy PDF content for testing page breaks. " * 200 * num_pages)
        return False


class TestGeminiExtractor(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = pathlib.Path(__file__).parent / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
        self.dummy_pdf_path = self.test_data_dir / "dummy.pdf"
        self.dummy_multi_page_pdf_path = self.test_data_dir / "dummy_multi_page.pdf"
        self.output_json_dir = self.test_data_dir / "output"
        self.output_json_dir.mkdir(exist_ok=True)
        self.dummy_pdf_dir = self.test_data_dir / "pdfs"
        self.dummy_pdf_dir.mkdir(exist_ok=True)


        # Create dummy PDF files for tests
        self.is_real_pdf_created = create_dummy_pdf(self.dummy_pdf_path, 1)
        self.is_real_multi_page_pdf_created = create_dummy_pdf(self.dummy_multi_page_pdf_path, 50) # 2 chunks

        # Mock environment variable for API key
        self.patcher = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

        # It's important to instantiate GeminiExtractor *after* the env var is patched
        self.extractor_with_key = GeminiExtractor(api_key="test_api_key")
        self.extractor_no_key_env = GeminiExtractor() # Will pick up from mocked env

    def tearDown(self):
        # Clean up created files
        if self.dummy_pdf_path.exists():
            self.dummy_pdf_path.unlink()
        if self.dummy_multi_page_pdf_path.exists():
            self.dummy_multi_page_pdf_path.unlink()
        for f in self.output_json_dir.glob("*.json"):
            f.unlink()
        if self.output_json_dir.exists():
            # Attempt to remove directory if empty
            try:
                self.output_json_dir.rmdir()
            except OSError: # Directory not empty, or other error
                pass
        if self.test_data_dir.exists():
            # Attempt to remove directory if empty
            try:
                self.test_data_dir.rmdir()
            except OSError: # Directory not empty, or other error
                pass

    def _create_pdf(self, path: pathlib.Path, pages: int) -> None:
        doc = fitz.open()
        for i in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i + 1}")
        doc.save(str(path))
        doc.close()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_for_test"})
    @patch.object(GeminiExtractor, "_extract_text_from_pdf")
    @patch("src.extractor.genai")
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
        result_path = extractor.extract_and_save_json(
            self.dummy_pdf_path, self.output_json_dir
        )
        self.assertIsNotNone(result_path)
        self.assertTrue(pathlib.Path(result_path).exists())
        mock_extract_text_from_pdf.assert_called_once_with(self.dummy_pdf_path)
        mock_genai.GenerativeModel.assert_called_once_with(extractor.model_name)
        self.assertEqual(mock_model_instance.generate_content.call_count, 1)


    @unittest.skipUnless(GeminiExtractor(api_key="dummy").is_configured(), "Gemini API not configured (no key or google.generativeai not installed)")
    @mock.patch("src.extractor.genai.GenerativeModel")
    def test_pdf_extraction_and_gemini_api_call_mocked(self, mock_generative_model):
        # This test focuses on the interaction with Gemini API (mocked) and basic PDF processing.
        # It does not deeply test the chunking logic, which is covered elsewhere.

        # Configure the mock for the Gemini API
        mock_model_instance = mock_generative_model.return_value
        mock_response = mock.Mock()
        # Example of a valid JSON response structure expected from Gemini
        mock_response.text = json.dumps([
            {
                "numero_processo": "1234567-89.2023.8.23.0001",
                "tipo_decisao": "sentença",
                "polo_ativo": ["Requerente Teste"],
                "advogados_polo_ativo": ["Advogado Teste (OAB/UF)"],
                "polo_passivo": ["Requerido Teste"],
                "advogados_polo_passivo": ["Advogado Passivo Teste (OAB/UF)"],
                "resultado": "procedente",
                "data": "2023-10-26",
                "resumo": "Teste de resumo da decisão."
            }
        ])
        mock_model_instance.generate_content.return_value = mock_response

        # Use the extractor instance that should have the API key
        extractor = self.extractor_with_key
        self.assertTrue(extractor.is_configured(), "Extractor should be configured with API key for this test.")

        result_path = extractor.extract_and_save_json(
            self.dummy_pdf_path, self.output_json_dir
        )

        self.assertIsNotNone(result_path)
        self.assertTrue(result_path.exists())
        mock_generative_model.assert_called_once_with(extractor.model_name)
        mock_model_instance.generate_content.assert_called() # Check that generate_content was called

        # Verify the content of the JSON output
        with open(result_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["file_name_source"], self.dummy_pdf_path.name)
        self.assertIn("decisions", data)
        self.assertEqual(len(data["decisions"]), 1) # Based on mocked response
        self.assertEqual(data["decisions"][0]["numero_processo"], "1234567-89.2023.8.23.0001")


    def test_pdf_chunking_logic(self):
        # This test specifically verifies the _extract_text_from_pdf method's chunking.
        # It requires PyMuPDF to be installed.
        if not self.is_real_multi_page_pdf_created:
            self.skipTest("PyMuPDF not available or dummy PDF creation failed, skipping chunking test.")

        # Use an extractor instance (API key presence doesn't matter for this private method test)
        extractor = self.extractor_no_key_env

        # PyMuPDF needs to be available for this test to be meaningful
        if not hasattr(extractor, "_extract_text_from_pdf") or extractor._extract_text_from_pdf.__qualname__.startswith("unittest.mock"):
             self.skipTest("PyMuPDF (fitz) is not installed or _extract_text_from_pdf is mocked unexpectedly.")


        # We created a 50-page PDF. Default chunk_size is 25. Expect 2 chunks.
        # extractor._extract_text_from_pdf is a private method, normally we'd test via public API
        # but here it's critical to test chunking directly.
        # If PyMuPDF is not installed, _extract_text_from_pdf will return [] and log an error.
        # The GeminiExtractor class has a check for 'fitz' module.

        # Check if fitz is available by attempting a dummy extraction
        # We need a valid path for this check, even if it's a dummy one.
        # Create a temporary dummy pdf for the check if not already present
        temp_pdf_for_check = self.test_data_dir / "temp_check.pdf"
        fitz_available_check_passed = False
        if create_dummy_pdf(temp_pdf_for_check, 1):
            if extractor._extract_text_from_pdf(temp_pdf_for_check) is not None: # Check if it returns list or None
                 fitz_available_check_passed = True
            if temp_pdf_for_check.exists():
                temp_pdf_for_check.unlink()

        if not fitz_available_check_passed:
             self.skipTest("PyMuPDF (fitz) is not available or _extract_text_from_pdf did not behave as expected for check, cannot test PDF text extraction.")


        chunks = extractor._extract_text_from_pdf(self.dummy_multi_page_pdf_path)

        # Based on 50 pages and chunk_size = 25 pages/chunk
        expected_num_chunks = (50 + 25 - 1) // 25 # ceiling division
        self.assertEqual(len(chunks), expected_num_chunks)

        if expected_num_chunks > 1:
            # Check for overlap markers if there are multiple chunks
            # The first chunk should not have "CONTINUAÇÃO DO TRECHO ANTERIOR"
            self.assertNotIn("CONTINUAÇÃO DO TRECHO ANTERIOR", chunks[0])
            # Subsequent chunks should have it
            for i in range(1, expected_num_chunks):
                self.assertIn("CONTINUAÇÃO DO TRECHO ANTERIOR", chunks[i])
                self.assertIn("NOVO TRECHO", chunks[i])

        # Check page numbering (simple check, assumes PyMuPDF extracts something)
        if chunks: # If PyMuPDF actually extracted text
            self.assertIn("PÁGINA 1", chunks[0])
            if expected_num_chunks > 0 and len(chunks) == expected_num_chunks : # check if chunks has expected_num_chunks elements
                if "PÁGINA 25" in chunks[0]: # If chunk size is 25
                     self.assertIn("PÁGINA 25", chunks[0])
                if expected_num_chunks > 1:
                    self.assertIn("PÁGINA 26", chunks[1]) # Start of the second chunk
                    # Check for overlap pages in the second chunk
                    self.assertIn("PÁGINA 25 (OVERLAP)", chunks[1])


    def test_gemini_api_integration_dummy_response_when_not_configured(self):
        # Temporarily remove the API key to simulate Gemini not being configured
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}): # Empty string for API key
            # Create a new extractor instance *within this context* so it picks up the cleared API key
            extractor_no_api = GeminiExtractor(api_key=None) # Explicitly pass None
            self.assertFalse(extractor_no_api.is_configured(), "Extractor should NOT be configured without API key.")

            result_path = extractor_no_api.extract_and_save_json(
                self.dummy_pdf_path, self.output_json_dir
            )
            self.assertIsNotNone(result_path)
            self.assertTrue(result_path.exists())

            with open(result_path, "r") as f:
                data = json.load(f)

            self.assertEqual(data["status"], "dummy_data_gemini_not_configured")
            self.assertEqual(data["numero_processo"], "0000000-00.0000.0.00.0000") # Check some dummy data fields


    def test_filename_sanitization(self):
        extractor = self.extractor_no_key_env # API key doesn't matter for this
        self.assertEqual(extractor._sanitize_filename("test.pdf"), "test.pdf")
        self.assertEqual(extractor._sanitize_filename("test file with spaces.pdf"), "testfilewithspaces.pdf")
        self.assertEqual(extractor._sanitize_filename("test-123_ABC.pdf"), "test-123_ABC.pdf")
        self.assertEqual(extractor._sanitize_filename("!@#$%^&*.pdf"), ".pdf") # Special chars removed
        self.assertEqual(extractor._sanitize_filename(""), "default_filename") # Empty filename


    @mock.patch("src.extractor.fitz", None)  # Simulate PyMuPDF not being installed
    def test_extraction_fails_gracefully_if_pymupdf_not_available(self):
        texts = self.extractor_with_key._extract_text_from_pdf(self.dummy_pdf_path)
        self.assertEqual(texts, [])

        result_path = self.extractor_with_key.extract_and_save_json(
            self.dummy_pdf_path, self.output_json_dir
        )
        self.assertIsNone(result_path)

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
    @patch("src.extractor.genai")
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
    @patch("src.extractor.genai")
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
    @patch("src.extractor.genai")
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


if __name__ == "__main__":
    unittest.main()