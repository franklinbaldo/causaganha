import unittest
from unittest.mock import patch, MagicMock
import sys
from io import StringIO
import logging
from pathlib import Path
import pandas as pd
import json
import argparse  # Added for Namespace
import tempfile
import shutil
from src import pipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Single import of pipeline module (resolved via conftest PYTHONPATH adjustments)


class TestPipelineArgParsingAndExecution(unittest.TestCase):
    def setUp(self):
        # Store original sys.argv and restore it in tearDown
        self.original_argv = sys.argv

        # Patch stdout and stderr
        self.stdout_patch = patch("sys.stdout", new_callable=StringIO)
        self.stderr_patch = patch("sys.stderr", new_callable=StringIO)
        self.mock_stdout = self.stdout_patch.start()
        self.mock_stderr = self.stderr_patch.start()

        # Basic logging setup for tests to capture output if needed
        # This avoids interference with the pipeline's own logging setup tests
        self.test_logger = logging.getLogger("test_pipeline_arg_parsing")
        self.log_capture_string = StringIO()
        self.ch = logging.StreamHandler(self.log_capture_string)
        self.ch.setLevel(logging.DEBUG)
        self.test_logger.addHandler(self.ch)
        self.test_logger.setLevel(logging.DEBUG)

    def tearDown(self):
        sys.argv = self.original_argv  # Restore original sys.argv
        self.stdout_patch.stop()
        self.stderr_patch.stop()
        if hasattr(self, "ch"):  # Clean up logging handler
            self.test_logger.removeHandler(self.ch)

    def run_main_for_test(self, args_list):
        # Mock sys.argv for argparse within pipeline.main()
        sys.argv = ["pipeline.py"] + args_list
        try:
            pipeline.main()  # pipeline.main() calls parser.parse_args()
            return 0  # Assuming main does not return a specific code on success
        except SystemExit as e:
            return e.code  # Argparse calls sys.exit on error
        except Exception as e:
            self.test_logger.error(
                f"run_main_for_test encountered an exception: {e}", exc_info=True
            )
            raise  # Re-raise other exceptions to fail the test clearly

    @patch(
        "src.pipeline.fetch_tjro_pdf"
    )  # Patching where it's defined/imported in pipeline.py
    def test_collect_args_parsed_and_called(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake.pdf")
        self.assertEqual(self.run_main_for_test(["collect", "--date", "2024-03-10"]), 0)
        mock_fetch.assert_called_once_with(
            date_str="2024-03-10", dry_run=False, verbose=False
        )

    @patch("src.pipeline.fetch_tjro_pdf")
    def test_collect_dry_run(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake_dry.pdf")
        self.assertEqual(
            self.run_main_for_test(["collect", "--date", "2024-03-11", "--dry-run"]), 0
        )
        mock_fetch.assert_called_once_with(
            date_str="2024-03-11", dry_run=True, verbose=False
        )

    @patch("src.pipeline.GeminiExtractor")  # Patching where it's defined/imported
    def test_extract_args_parsed_and_called(self, MockGeminiExtractor):
        mock_instance = MockGeminiExtractor.return_value
        mock_instance.extract_and_save_json.return_value = Path("/tmp/fake.json")

        # Create a dummy PDF in a temporary location for the test
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            dummy_pdf_path = Path(tmp_pdf.name)

        self.assertEqual(
            self.run_main_for_test(
                [
                    "extract",
                    "--pdf_file",
                    str(dummy_pdf_path),
                    "--output_json_dir",
                    "/tmp/output",
                ]
            ),
            0,
        )
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        mock_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=dummy_pdf_path, output_json_dir=Path("/tmp/output"), dry_run=False
        )
        if dummy_pdf_path.exists():
            dummy_pdf_path.unlink()

    @patch("src.pipeline.GeminiExtractor")
    def test_extract_dry_run(self, MockGeminiExtractor):
        mock_instance = MockGeminiExtractor.return_value
        mock_instance.extract_and_save_json.return_value = Path("/tmp/fake_dry.json")
        # Use a dummy path string as the file doesn't need to exist for dry-run
        dummy_pdf_path_str = "/tmp/dummy_for_extract_dry.pdf"

        self.assertEqual(
            self.run_main_for_test(
                ["extract", "--pdf_file", dummy_pdf_path_str, "--dry-run"]
            ),
            0,
        )
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        mock_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=Path(dummy_pdf_path_str),
            output_json_dir=Path("/tmp"),  # Default output is parent of pdf_file
            dry_run=True,
        )

    @patch("src.pipeline.update_command")
    @patch("src.pipeline.GeminiExtractor")
    @patch("src.pipeline.fetch_tjro_pdf")
    def test_run_command_orchestration(
        self, mock_fetch, MockGeminiExtractor, mock_update_cmd
    ):
        mock_fetch.return_value = Path("/tmp/collected_via_run.pdf")
        mock_extractor_instance = MockGeminiExtractor.return_value
        # Ensure the path exists for the 'extract' step if it writes a dummy file
        expected_json_output_dir = Path("data/json/")
        expected_json_output_dir.mkdir(parents=True, exist_ok=True)
        mock_extractor_instance.extract_and_save_json.return_value = (
            expected_json_output_dir / "run_extracted.json"
        )

        self.assertEqual(self.run_main_for_test(["run", "--date", "2024-03-12"]), 0)
        mock_fetch.assert_called_once_with(
            date_str="2024-03-12", dry_run=False, verbose=False
        )
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        mock_extractor_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=Path("/tmp/collected_via_run.pdf"),
            output_json_dir=expected_json_output_dir,  # Check against the default
            dry_run=False,
        )
        mock_update_cmd.assert_called_once()

    @patch("src.pipeline.update_command")
    @patch("src.pipeline.GeminiExtractor")
    @patch("src.pipeline.fetch_tjro_pdf")
    def test_run_command_dry_run(
        self, mock_fetch, MockGeminiExtractor, mock_update_cmd
    ):
        mock_fetch.return_value = Path("/tmp/collected_dry_run.pdf")
        mock_extractor_instance = MockGeminiExtractor.return_value
        expected_json_output_dir = Path("data/json/")
        mock_extractor_instance.extract_and_save_json.return_value = (
            expected_json_output_dir / "run_extracted_dry.json"
        )

        self.assertEqual(
            self.run_main_for_test(
                ["--verbose", "run", "--date", "2024-03-13", "--dry-run"]
            ),
            0,
        )
        mock_fetch.assert_called_once_with(
            date_str="2024-03-13", dry_run=True, verbose=True
        )
        MockGeminiExtractor.assert_called_once_with(verbose=True)
        mock_extractor_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=Path("/tmp/collected_dry_run.pdf"),
            output_json_dir=expected_json_output_dir,  # Check against the default
            dry_run=True,
        )
        mock_update_cmd.assert_called_once()
        self.assertTrue(mock_update_cmd.call_args[0][0].dry_run)

    def test_unknown_argument(self):
        # argparse in Python 3.9+ exits with 2 for argument errors
        self.assertEqual(self.run_main_for_test(["collect", "--date", "2024-01-01", "--nonexistent-arg"]), 2)
        self.assertIn(
            "unrecognized arguments: --nonexistent-arg", self.mock_stderr.getvalue()
        )

    def test_unknown_subcommand_argument(self):
        self.assertEqual(self.run_main_for_test(["update", "--nonexistent-arg"]), 2)
        self.assertIn(
            "unrecognized arguments: --nonexistent-arg", self.mock_stderr.getvalue()
        )

    def test_collect_missing_date(self):
        self.assertEqual(self.run_main_for_test(["collect"]), 2)
        self.assertIn(
            "the following arguments are required: --date", self.mock_stderr.getvalue()
        )

    def test_extract_missing_pdf_file(self):
        self.assertEqual(self.run_main_for_test(["extract"]), 2)
        self.assertIn(
            "the following arguments are required: --pdf_file",
            self.mock_stderr.getvalue(),
        )

    @patch("src.pipeline.fetch_tjro_pdf")
    def test_collect_invalid_date_format_passed_through(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake_invalid_date.pdf")
        # The custom fetch_tjro_pdf in pipeline.py has its own date parsing.
        # If it fails, it logs an error and returns None. The main() would then just proceed.
        # This test should ideally check for the logged error or that no file is processed further.
        # For now, checking that fetch is called.
        self.assertEqual(
            self.run_main_for_test(["collect", "--date", "NOT-A-DATE"]), 0
        )  # main() might not exit with error code here
        mock_fetch.assert_called_once_with(
            date_str="NOT-A-DATE", dry_run=False, verbose=False
        )

    @patch("logging.basicConfig")
    def test_verbose_flag_sets_debug_level_basicConfig(self, mock_basic_config):
        # Patch the function that would normally run after parsing to avoid its side effects
        with patch.object(pipeline, "update_command", MagicMock()):
            self.run_main_for_test(["--verbose", "update"])

        # Check if basicConfig was called with level=logging.DEBUG
        # This can be tricky if basicConfig is called multiple times or by other modules.
        # A more robust test might check the effective level of a specific logger.
        debug_call_found = False
        for call_args_tuple in mock_basic_config.call_args_list:
            if call_args_tuple.kwargs.get("level") == logging.DEBUG:
                debug_call_found = True
                break
        self.assertTrue(
            debug_call_found, "logging.basicConfig was not called with logging.DEBUG"
        )

    @patch("logging.getLogger")  # Patch getLogger used by pipeline.py
    def test_verbose_logging_capture_for_update(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        with patch.object(pipeline, "_update_ratings_logic", MagicMock()):
            self.run_main_for_test(["--verbose", "update"])

        # Check if debug was called and if specific messages were logged
        self.assertTrue(mock_logger_instance.debug.called)
        self.assertTrue(
            any(
                "Update command called with args" in str(call_arg)
                for call_arg in mock_logger_instance.debug.call_args_list
            )
        )

    @patch("logging.getLogger")
    def test_dry_run_logging_capture_for_collect(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        # Don't patch fetch_tjro_pdf so we can test the dry-run logging behavior
        self.run_main_for_test(["collect", "--date", "2024-01-01", "--dry-run"])

        dry_run_fetch_logged = any(
            "DRY-RUN: Would fetch TJRO PDF for date: 2024-01-01" in str(call_arg)
            for call_arg in mock_logger_instance.info.call_args_list
        )
        self.assertTrue(
            dry_run_fetch_logged,
            f"Expected DRY-RUN info log not found. Actual: {mock_logger_instance.info.call_args_list}",
        )


class TestPipelineUpdateCommand(unittest.TestCase):
    # This class needs substantial rework if _update_ratings_logic is complex
    # and involves file I/O or external calls that need mocking.
    # For now, keeping it simple and assuming it might fail due to module import.
    def setUp(self):
        if pipeline is None:
            self.fail("The 'pipeline' module could not be imported.")

        self.test_data_root = Path(tempfile.mkdtemp(prefix="causaganha_pipeline_test_"))
        self.json_input_dir = self.test_data_root / "json"
        self.processed_json_dir = self.test_data_root / "json_processed"
        self.ratings_csv_path = self.test_data_root / "ratings.csv"
        self.partidas_csv_path = self.test_data_root / "partidas.csv"

        self.json_input_dir.mkdir(parents=True, exist_ok=True)
        self.processed_json_dir.mkdir(parents=True, exist_ok=True)

        # Sample data (simplified)
        self.sample_decision_1 = {
            "numero_processo": "1234567-89.2023.8.23.0001",
            "resultado": "procedente",
            "advogados_polo_ativo": ["AdvA"],
            "advogados_polo_passivo": ["AdvB"],
            "data_decisao": "2023-01-01",
            "polo_ativo": "Test Requerente",
            "polo_passivo": "Test Requerido",
        }
        with open(self.json_input_dir / "decision1.json", "w") as f:
            json.dump({"decisions": [self.sample_decision_1]}, f)

        pd.DataFrame(columns=["mu", "sigma", "total_partidas"]).set_index(
            pd.Index([], name="advogado_id")
        ).to_csv(self.ratings_csv_path)

        self.stdout_patch = patch("sys.stdout", new_callable=StringIO)
        self.mock_stdout = self.stdout_patch.start()

    def tearDown(self):
        shutil.rmtree(self.test_data_root)
        self.stdout_patch.stop()

    @patch("src.pipeline.pd.read_csv")
    @patch("src.pipeline.pd.DataFrame.to_csv")
    @patch("src.pipeline.shutil.move")
    def test_update_command_valid_decisions(
        self, mock_move, mock_to_csv, mock_read_csv
    ):
        # Mock read_csv to return an empty DataFrame initially
        mock_read_csv.return_value = pd.DataFrame(
            columns=["mu", "sigma", "total_partidas"]
        ).set_index(pd.Index([], name="advogado_id"))

        args = argparse.Namespace(
            dry_run=False, verbose=False
        )  # Use argparse.Namespace
        
        # Patch CONFIG to use test directory
        with patch("src.pipeline.CONFIG", {"data_dir": str(self.test_data_root)}):
            pipeline.update_command(args)  # Call the command function

        self.assertTrue(mock_read_csv.called)
        self.assertTrue(mock_to_csv.called)  # Should be called for ratings and partidas
        # Move should be called since we have test JSON files
        self.assertTrue(mock_move.called)  # For moving processed JSON

    @patch("src.pipeline.pd.read_csv")
    @patch("src.pipeline.pd.DataFrame.to_csv")
    @patch("src.pipeline.shutil.move")
    def test_update_command_dry_run(self, mock_move, mock_to_csv, mock_read_csv):
        mock_read_csv.return_value = pd.DataFrame(
            columns=["mu", "sigma", "total_partidas"]
        ).set_index(pd.Index([], name="advogado_id"))
        args = argparse.Namespace(dry_run=True, verbose=False)
        
        # Patch CONFIG to use test directory
        with patch("src.pipeline.CONFIG", {"data_dir": str(self.test_data_root)}):
            pipeline.update_command(args)
        self.assertTrue(mock_read_csv.called)
        mock_to_csv.assert_not_called()
        mock_move.assert_not_called()

    @patch(
        "src.pipeline.validate_decision", return_value=False
    )  # All decisions invalid
    @patch("src.pipeline.pd.read_csv")
    @patch("src.pipeline.pd.DataFrame.to_csv")
    @patch("src.pipeline.shutil.move")
    def test_update_command_all_decisions_invalid(
        self, mock_move, mock_to_csv, mock_read_csv, mock_validate
    ):
        mock_read_csv.return_value = pd.DataFrame(
            columns=["mu", "sigma", "total_partidas"]
        ).set_index(pd.Index([], name="advogado_id"))
        args = argparse.Namespace(dry_run=False, verbose=False)
        
        # Patch CONFIG to use test directory
        with patch("src.pipeline.CONFIG", {"data_dir": str(self.test_data_root)}):
            pipeline.update_command(args)
        # Ratings file might still be saved even if empty or unchanged
        self.assertTrue(mock_to_csv.called)
        # No files should be moved if no valid decisions processed
        mock_move.assert_not_called()
        # Validate should be called since we have test JSON files
        self.assertTrue(mock_validate.called)


if __name__ == "__main__":
    # logging.disable(logging.NOTSET) # Ensure logging is enabled for manual runs
    # logging.basicConfig(level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s")
    unittest.main(argv=sys.argv[:1], verbosity=2, exit=False)
