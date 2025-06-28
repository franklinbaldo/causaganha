import sys
import json
import tempfile
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch, mock_open

# Ensure src directory on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ia_discovery import main  # noqa: E402


class TestIADiscoveryCLI(unittest.TestCase):
    def setUp(self):
        self.original_argv = sys.argv
        self.stdout_patch = patch("sys.stdout", new_callable=StringIO)
        self.mock_stdout = self.stdout_patch.start()
        self.stderr_patch = patch("sys.stderr", new_callable=StringIO)
        self.mock_stderr = self.stderr_patch.start()

        self.sample_search_items = [
            {"identifier": "ia-2025-01-01", "date": "2025-01-01"},
            {"identifier": "ia-2025-01-02", "date": "2025-01-02"},
            {"identifier": "ia-2025-01-04", "date": "2025-01-04"},
        ]
        self.sample_details = {"metadata": {"title": "TJRO"}, "files": []}
        self.sample_pipeline_data = [
            {"date": "2025-01-01", "year": 2025},
            {"date": "2025-01-02", "year": 2025},
            {"date": "2025-01-03", "year": 2025},
        ]

    def tearDown(self):
        sys.argv = self.original_argv
        self.stdout_patch.stop()
        self.stderr_patch.stop()

    def run_cli(self, args):
        sys.argv = ["ia_discovery.py"] + args
        return main()

    @patch("ia_discovery.IADiscovery.get_detailed_item_info")
    @patch("ia_discovery.IADiscovery.search_tjro_diarios")
    def test_coverage_report_cli(self, mock_search, mock_detail):
        mock_search.return_value = self.sample_search_items
        mock_detail.return_value = self.sample_details
        mopen = mock_open(read_data=json.dumps(self.sample_pipeline_data))
        with patch("ia_discovery.open", mopen):
            exit_code = self.run_cli(["--coverage-report", "--year", "2025"])
        self.assertEqual(exit_code, 0)
        output = self.mock_stdout.getvalue()
        self.assertIn("Coverage:", output)
        self.assertIn("66.7%", output)
        self.assertIn("Missing: 1", output)
        self.assertIn("Extra: 1", output)

    @patch("ia_discovery.IADiscovery.get_detailed_item_info")
    @patch("ia_discovery.IADiscovery.search_tjro_diarios")
    def test_export_inventory_cli(self, mock_search, mock_detail):
        mock_search.return_value = self.sample_search_items
        mock_detail.return_value = self.sample_details
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "inv.json"
            exit_code = self.run_cli(["--export", str(out_file), "--year", "2025"])
            self.assertEqual(exit_code, 0)
            data = json.loads(out_file.read_text())
            self.assertEqual(data["query_year"], 2025)
            self.assertEqual(data["total_items"], len(self.sample_search_items))
            self.assertEqual(len(data["items"]), len(self.sample_search_items))
            self.assertIn("generated_at", data)


if __name__ == "__main__":
    unittest.main()