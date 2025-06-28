import unittest
import pathlib
import json
from unittest import mock
from datetime import datetime

# Attempt to import the class to be tested
try:
    from src.ia_discovery import IADiscovery
except ImportError:
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    from src.ia_discovery import IADiscovery
    import requests # Import requests here for the exception

# Helper function to simulate responses from requests.get
def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code, text_data=None):
            self.json_data = json_data
            self.status_code = status_code
            self.text = text_data if text_data is not None else json.dumps(json_data)

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                # Ensure requests.exceptions is accessible
                raise requests.exceptions.HTTPError(f"Mocked HTTP Error {self.status_code}")

    # Mocking archive.org/advancedsearch.php
    if args[0].startswith("https://archive.org/advancedsearch.php"):
        params = kwargs.get("params", {})
        query = params.get("q", "")
        # Simulate different responses based on query or other params if needed
        if 'tjro-diario-2023-01-01' in query or "2023" in query : # Simplified check
            return MockResponse({
                "response": {
                    "docs": [
                        {"identifier": "tjro-diario-2023-01-01", "title": "Diário Teste 1", "date": "2023-01-01T00:00:00Z", "downloads": 10, "item_size": 1024},
                        {"identifier": "tjro-diario-2023-01-02", "title": "Diário Teste 2", "date": "2023-01-02T00:00:00Z", "downloads": 5, "item_size": 2048},
                    ]
                }
            }, 200)
        return MockResponse({"response": {"docs": []}}, 200)

    # Mocking archive.org/metadata/{identifier}
    elif args[0].startswith("https://archive.org/metadata/"):
        identifier = args[0].split("/")[-1]
        if identifier == "tjro-diario-2023-01-01":
            return MockResponse({
                "metadata": {"title": "Diário Teste 1", "date": "2023-01-01", "creator": "Tribunal de Justiça de Rondônia"},
                "files": [{"name": "tjro-diario-2023-01-01.pdf", "format": "PDF"}]
            }, 200)
        elif identifier == "tjro-diario-nonexistent":
             return MockResponse(None, 404, text_data="Not found") # Simulate 404
        return MockResponse({}, 404, text_data="Not found") # Default to not found for other metadata calls

    return MockResponse(None, 404, text_data="Unhandled mock URL")

def mocked_requests_head(*args, **kwargs):
    class MockResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    if args[0].startswith("https://archive.org/metadata/"):
        identifier = args[0].split("/")[-1]
        if identifier == "tjro-diario-2023-01-01-exists": # Specific identifier for HEAD check
            return MockResponse(200)
        return MockResponse(404)
    return MockResponse(404)


class TestIADiscoveryIntegration(unittest.TestCase):
    def setUp(self):
        self.discovery = IADiscovery()
        self.test_output_dir = pathlib.Path(__file__).parent / "test_ia_output"
        self.test_output_dir.mkdir(exist_ok=True)
        self.pipeline_data_file = self.test_output_dir / "diarios_pipeline_ready.json"

        # Create a dummy pipeline data file for coverage tests
        dummy_pipeline_data = [
            {"date": "2023-01-01", "year": 2023, "status": "processed"},
            {"date": "2023-01-02", "year": 2023, "status": "processed"},
            {"date": "2023-01-03", "year": 2023, "status": "pending"}, # This one is missing in mock IA data
        ]
        with open(self.pipeline_data_file, "w") as f:
            json.dump(dummy_pipeline_data, f)

    def tearDown(self):
        for f in self.test_output_dir.glob("*"):
            f.unlink()
        if self.test_output_dir.exists():
            self.test_output_dir.rmdir()

    @mock.patch("src.ia_discovery.requests.get", side_effect=mocked_requests_get)
    def test_search_tjro_diarios_integration(self, mock_get):
        """Test searching for TJRO diarios, mocking the HTTP GET request."""
        items = self.discovery.search_tjro_diarios(year=2023)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["identifier"], "tjro-diario-2023-01-01")
        mock_get.assert_called() # Check that requests.get was called

    @mock.patch("src.ia_discovery.requests.get", side_effect=mocked_requests_get)
    def test_get_detailed_item_info_integration(self, mock_get):
        """Test getting detailed info, mocking HTTP GET."""
        details = self.discovery.get_detailed_item_info("tjro-diario-2023-01-01")
        self.assertIsNotNone(details)
        self.assertEqual(details["metadata"]["title"], "Diário Teste 1")

        not_found_details = self.discovery.get_detailed_item_info("tjro-diario-nonexistent")
        self.assertIsNone(not_found_details) # Based on current mock which returns 404 then None
        mock_get.assert_called()


    @mock.patch("src.ia_discovery.requests.get", side_effect=mocked_requests_get)
    def test_generate_coverage_report_integration(self, mock_get):
        """Test coverage report generation, mocking HTTP and file operations."""

        # Read the content of our dummy pipeline file
        with open(self.pipeline_data_file, "r") as f:
            dummy_content = f.read()

        # Path used in the source code that we need to mock
        original_pipeline_file_path = "data/diarios_pipeline_ready.json"

        # Mock builtins.open. When called with original_pipeline_file_path,
        # it will return a mock file object with dummy_content.
        # Otherwise, it will delegate to the original open (though not strictly needed here as only one open matters).
        m = mock.mock_open(read_data=dummy_content)

        # This lambda function acts as a dispatcher for open calls.
        # If the file path matches our target, it uses the mock 'm'.
        # Otherwise (and this part is crucial for robustness if other files were opened by the tested code),
        # it would fall back to the real open. For this specific test, only one 'open' call is expected
        # to be for 'data/diarios_pipeline_ready.json'.
        def open_side_effect(file, *args, **kwargs):
            if file == original_pipeline_file_path:
                return m(file, *args, **kwargs)
            # Fallback for any other file paths, though not expected in this specific method
            return mock. ursprüng_open(file, *args, **kwargs)


        with mock.patch('builtins.open', side_effect=open_side_effect) as mock_builtin_open:
            report = self.discovery.generate_coverage_report(year=2023)

        self.assertEqual(report["year"], 2023)
        self.assertEqual(report["total_in_ia"], 2) # From mocked search_tjro_diarios
        self.assertEqual(report["total_expected"], 3) # From dummy_pipeline_data
        self.assertAlmostEqual(report["coverage_percentage"], (2/3)*100)
        self.assertEqual(report["missing_count"], 1)
        self.assertIn("2023-01-03", report["missing_dates"])
        mock_get.assert_called()
        # Verify that builtins.open was called with the correct path
        # m.assert_any_call(original_pipeline_file_path, 'r') # This check is on the mock_open instance itself
        # A more direct check on mock_builtin_open:
        # Check if it was called with the specific path. This is a bit more complex due to the side_effect.
        # A simpler check is to ensure the mock 'm' (which handles our target file) was called.
        m.assert_called_with(original_pipeline_file_path, 'r')


    @mock.patch("src.ia_discovery.requests.get", side_effect=mocked_requests_get)
    @mock.patch("src.ia_discovery.json.dump") # Mock json.dump to avoid actual file writing
    @mock.patch("builtins.open", new_callable=mock.mock_open) # Mock open to avoid file writing
    def test_export_ia_inventory_integration(self, mock_open_call, mock_json_dump, mock_get):
        """Test IA inventory export, mocking HTTP and file operations."""
        output_filename = str(self.test_output_dir / "inventory_export.json")
        self.discovery.export_ia_inventory(output_filename, year=2023)

        mock_get.assert_called() # search_tjro_diarios and get_detailed_item_info (for first 10)

        # Check that 'open' was called with the correct filename and mode
        mock_open_call.assert_called_with(output_filename, "w", encoding="utf-8")

        # Check that json.dump was called
        mock_json_dump.assert_called_once()

        # Inspect what was passed to json.dump (first argument of the first call)
        dump_args, _ = mock_json_dump.call_args
        exported_data = dump_args[0]

        self.assertEqual(exported_data["query_year"], 2023)
        self.assertEqual(exported_data["total_items"], 2) # From mocked search
        self.assertTrue(len(exported_data["items"]) <= 10) # Export enhances <=10 items
        if exported_data["items"]: # If items were returned by mock
             self.assertIn("detailed_metadata", exported_data["items"][0]) # Check enhanced data


    @mock.patch("src.ia_discovery.requests.head", side_effect=mocked_requests_head)
    def test_check_identifier_exists_integration(self, mock_head):
        """Test checking if an identifier exists, mocking HTTP HEAD."""
        self.assertTrue(self.discovery.check_identifier_exists("tjro-diario-2023-01-01-exists"))
        self.assertFalse(self.discovery.check_identifier_exists("tjro-diario-does-not-exist"))
        mock_head.assert_called()

if __name__ == "__main__":
    # Need to import requests for the mocked_requests_get to work correctly with raise_for_status
    import requests
    unittest.main()
