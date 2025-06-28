import unittest
import time
import pathlib
import os
import json
from unittest import mock

# Setup sys.path for src imports if tests are run from a different working dir
try:
    from src.extractor import GeminiExtractor
    from src.ia_discovery import IADiscovery
except ImportError:
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
    from src.extractor import GeminiExtractor
    from src.ia_discovery import IADiscovery

# Helper to create dummy PDF (copied from test_extractor.py - consider refactoring to a shared test utils module)
def create_dummy_pdf(path, num_pages=1):
    try:
        from PyPDF2 import PdfWriter

        writer = PdfWriter()
        for _ in range(num_pages):
            writer.add_blank_page(width=612, height=792)
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
            f.write("Dummy PDF content " * 100 * num_pages)
        return False

# Mock for IADiscovery tests (similar to test_ia_discovery.py)
def mocked_ia_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
        def json(self):
            return self.json_data
        def raise_for_status(self):
            pass
    if args[0].startswith("https://archive.org/advancedsearch.php"):
        return MockResponse({"response": {"docs": [{"identifier": f"fake_id_{i}"} for i in range(100)]}}, 200)
    return MockResponse({}, 404)


class TestPipelineBenchmarks(unittest.TestCase):

    def setUp(self):
        self.test_files_dir = pathlib.Path(__file__).parent / "benchmark_files"
        self.test_files_dir.mkdir(exist_ok=True)
        self.dummy_pdf_path = self.test_files_dir / "benchmark_dummy.pdf"
        self.real_pdf_created = create_dummy_pdf(self.dummy_pdf_path, 10)

        # Mock GEMINI_API_KEY for GeminiExtractor
        self.patcher = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "benchmark_fake_key"})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

        self.extractor = GeminiExtractor(api_key="benchmark_fake_key")
        self.ia_discovery = IADiscovery()

    def tearDown(self):
        if self.dummy_pdf_path.exists():
            self.dummy_pdf_path.unlink()

        # Improved cleanup for files and directories
        if self.test_files_dir.exists():
            import shutil
            for item in self.test_files_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink(missing_ok=True)
            # Finally, remove the main benchmark_files directory if it's empty
            try:
                self.test_files_dir.rmdir()
            except OSError: # Dir not empty or other error
                pass # Or log a warning

    @mock.patch("src.extractor.genai.GenerativeModel")
    def test_benchmark_gemini_extractor_pdf_processing(self, mock_generative_model):
        """Benchmark GeminiExtractor.extract_and_save_json (with mocked API)."""
        if not self.real_pdf_created:
            self.skipTest("PyPDF2 or fitz not available to create valid PDF")
        # Configure the mock for the Gemini API
        mock_model_instance = mock_generative_model.return_value
        mock_response = mock.Mock()
        mock_response.text = json.dumps([{"numero_processo": "bench-123"}])
        mock_model_instance.generate_content.return_value = mock_response

        # Ensure extractor is "configured" for this test path
        self.extractor.gemini_configured = True

        output_dir = self.test_files_dir / "extractor_output"
        output_dir.mkdir(exist_ok=True)

        start_time = time.perf_counter()

        # Run the extraction multiple times for better measurement
        num_runs = 5
        for _ in range(num_runs):
            result_path = self.extractor.extract_and_save_json(self.dummy_pdf_path, output_dir)
            # Minimal check to ensure it ran
            self.assertIsNotNone(result_path)
            if result_path and result_path.exists():
                result_path.unlink() # Clean up between runs

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_per_run = total_time / num_runs

        print(f"\n[BENCHMARK] GeminiExtractor PDF Processing (mocked API, {num_runs} runs):")
        print(f"  Total time: {total_time:.4f} seconds")
        print(f"  Average time per PDF (10 pages): {avg_time_per_run:.4f} seconds")

        # Basic assertion: ensure it's not unexpectedly slow (e.g., > 1 second per run for this mock)
        self.assertTrue(avg_time_per_run < 1.0, f"Extractor benchmark too slow: {avg_time_per_run:.4f}s")

    @mock.patch("src.ia_discovery.requests.get", side_effect=mocked_ia_requests_get)
    def test_benchmark_ia_discovery_search(self, mock_get):
        """Benchmark IADiscovery.search_tjro_diarios (mocked HTTP)."""
        start_time = time.perf_counter()

        num_runs = 10
        for _ in range(num_runs):
            items = self.ia_discovery.search_tjro_diarios(year=2024, rows=100)
            # Minimal check
            self.assertTrue(len(items) > 0)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_per_run = total_time / num_runs

        print(f"\n[BENCHMARK] IADiscovery Search (mocked HTTP, {num_runs} runs):")
        print(f"  Total time: {total_time:.4f} seconds")
        print(f"  Average time per search: {avg_time_per_run:.4f} seconds")

        # Basic assertion: ensure it's not unexpectedly slow (e.g., > 0.1 seconds per run for this mock)
        self.assertTrue(avg_time_per_run < 0.1, f"IA Discovery search benchmark too slow: {avg_time_per_run:.4f}s")

    # TODO: Add benchmarks for actual database operations once db setup for tests is clearer.
    # For example, inserting N records, querying records, etc.
    # This would likely involve setting up a test database.

if __name__ == "__main__":
    # This allows running benchmarks individually using:
    # python -m tests.benchmarks.test_pipeline_benchmark TestPipelineBenchmarks.benchmark_gemini_extractor_pdf_processing
    # python -m tests.benchmarks.test_pipeline_benchmark TestPipelineBenchmarks.benchmark_ia_discovery_search
    # Or all benchmarks in the file:
    # python -m unittest tests.benchmarks.test_pipeline_benchmark

    # For more structured benchmark running and reporting, pytest-benchmark is recommended.
    # For now, we use print statements and basic assertions.

    suite = unittest.TestSuite()
    # Manually add tests if you want to control execution order or selection for direct script run
    # suite.addTest(TestPipelineBenchmarks('benchmark_gemini_extractor_pdf_processing'))
    # suite.addTest(TestPipelineBenchmarks('benchmark_ia_discovery_search'))
    # runner = unittest.TextTestRunner(verbosity=2)
    # runner.run(suite)

    # Default behavior: run all tests in the class if script is executed directly
    unittest.main(verbosity=2)
