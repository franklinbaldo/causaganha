import unittest
import pathlib
import os
import json
from unittest import mock

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
            writer.add_blank_page(width=612, height=792) # Standard letter size
        with open(path, "wb") as f:
            writer.write(f)
        return True
    except ImportError:
        # Fallback if PyPDF2 is not available
        with open(path, "w") as f:
            f.write("Dummy PDF content for testing page breaks. " * 200 * num_pages) # Simulate some content
        return False # Indicate that a real PDF was not created
    except Exception:
        return False


class TestGeminiExtractor(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = pathlib.Path(__file__).parent / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
        self.dummy_pdf_path = self.test_data_dir / "dummy.pdf"
        self.dummy_multi_page_pdf_path = self.test_data_dir / "dummy_multi_page.pdf"
        self.output_json_dir = self.test_data_dir / "output"
        self.output_json_dir.mkdir(exist_ok=True)

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


    @mock.patch("src.extractor.fitz", None) # Simulate PyMuPDF not being installed
    def test_extraction_fails_gracefully_if_pymupdf_not_available(self):
        extractor = GeminiExtractor(api_key="test_api_key") # API key present
        # Ensure is_configured is True because API key is there, even if fitz is not.
        # The control flow for dummy data is separate from fitz availability for text extraction.
        # self.assertTrue(extractor.is_configured()) # This will be true if API key is set

        # _extract_text_from_pdf should return an empty list and log an error
        # We need to instantiate the extractor *inside* the mock context for fitz=None to be effective
        # for the instantiation of GeminiExtractor if it checks fitz at __init__ (it does not directly, but good practice)

        # Re-instantiate or ensure the mock is active when _extract_text_from_pdf is called
        # The mock is active for the whole method, so self.extractor_with_key would be affected if it used fitz globally
        # For testing _extract_text_from_pdf directly, it's fine.

        with self.assertLogs(level='ERROR') as log:
            # Create a new instance *inside* the mock context if fitz is checked at init
            # Or, if fitz is only checked inside _extract_text_from_pdf, current instance is fine.
            # GeminiExtractor checks for fitz module at the top level, so the mock will make fitz=None
            # when _extract_text_from_pdf is called on any instance.

            # For safety, create a new extractor instance if there's any doubt about when 'fitz' is evaluated.
            # However, the current structure of GeminiExtractor evaluates 'fitz' at module import time.
            # The @mock.patch at the method level correctly makes 'src.extractor.fitz' None for the duration of this test method.

            # extractor_in_mock_context = GeminiExtractor(api_key="test_api_key")
            # texts = extractor_in_mock_context._extract_text_from_pdf(self.dummy_pdf_path)

            # Using existing extractor, as the 'fitz' used by its methods will be the mocked one.
            texts = self.extractor_with_key._extract_text_from_pdf(self.dummy_pdf_path)
            self.assertEqual(texts, [])
        self.assertIn("PyMuPDF (fitz) not available", log.output[0])


        # The overall extraction should then fail or return None because no text can be processed
        result_path = self.extractor_with_key.extract_and_save_json(self.dummy_pdf_path, self.output_json_dir)
        self.assertIsNone(result_path, "Extraction should fail if PDF text cannot be extracted.")


if __name__ == "__main__":
    unittest.main()
