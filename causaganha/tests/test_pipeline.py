import unittest
from unittest.mock import patch, MagicMock, call
import sys
from io import StringIO
import logging
from pathlib import Path

# Add project root to sys.path to allow importing causaganha
# This is often needed when running tests directly, depending on execution context
# For the sandbox, it might be implicitly handled if /app is the root.
# However, good practice for local testing.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Attempt to import the module under test
try:
    from causaganha.legalelo import pipeline
except ModuleNotFoundError as e:
    # Provide more context if the import fails.
    print(f"ERROR: Could not import causaganha.legalelo.pipeline. Original error: {e}", file=sys.stderr)
    print(f"PROJECT_ROOT: {PROJECT_ROOT}", file=sys.stderr)
    print(f"sys.path: {sys.path}", file=sys.stderr)
    # To make tests fail clearly if the import fails, we can re-raise or set pipeline to None
    # and check in setUp. For now, printing to stderr might be visible in test output.
    pipeline = None # Or raise ImportError("Module causaganha.legalelo.pipeline could not be loaded")

class TestPipelineArgParsingAndExecution(unittest.TestCase):

    def setUp(self):
        # Ensure the pipeline module is available before each test
        if pipeline is None:
            self.fail("The 'pipeline' module from 'causaganha.legalelo' could not be imported. Check PYTHONPATH and import errors.")

        # Suppress print output from the pipeline and argparse errors to stderr.
        self.stdout_patch = patch('sys.stdout', new_callable=StringIO)
        self.stderr_patch = patch('sys.stderr', new_callable=StringIO)
        self.mock_stdout = self.stdout_patch.start()
        self.mock_stderr = self.stderr_patch.start()

        # Reset logging handlers to ensure a clean state for each test.
        # This prevents interference between tests, especially since pipeline.setup_logging
        # manipulates root handlers.
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Also, clear handlers for the specific logger used within the pipeline module.
        # This ensures that patched loggers in one test don't affect others.
        pipeline_module_logger = logging.getLogger('causaganha.legalelo.pipeline')
        for handler in pipeline_module_logger.handlers[:]:
            pipeline_module_logger.removeHandler(handler)
        pipeline_module_logger.setLevel(logging.NOTSET) # Reset level too


    def tearDown(self):
        self.stdout_patch.stop()
        self.stderr_patch.stop()

    # Helper to run pipeline.main and capture SystemExit
    def run_main_for_test(self, args_list):
        """Runs pipeline.main with given args and returns exit code or 0 for success."""
        # Store original sys.argv
        original_argv = sys.argv
        try:
            # Argparse expects the first argument to be the program name
            sys.argv = ['pipeline.py'] + args_list
            pipeline.main() # main now uses sys.argv directly
            return 0 # Success
        except SystemExit as e:
            return e.code # Argparse calls sys.exit(2) on error, sys.exit(0) on --help
        finally:
            # Restore original sys.argv
            sys.argv = original_argv


    @patch('causaganha.legalelo.pipeline.fetch_tjro_pdf')
    def test_collect_args_parsed_and_called(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake.pdf")
        self.assertEqual(self.run_main_for_test(['collect', '--date', '2024-03-10']), 0)
        mock_fetch.assert_called_once_with(date_str='2024-03-10', dry_run=False, verbose=False)

    @patch('causaganha.legalelo.pipeline.fetch_tjro_pdf')
    def test_collect_dry_run(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake_dry.pdf")
        self.assertEqual(self.run_main_for_test(['collect', '--date', '2024-03-11', '--dry-run']), 0)
        mock_fetch.assert_called_once_with(date_str='2024-03-11', dry_run=True, verbose=False)

    @patch('causaganha.legalelo.pipeline.GeminiExtractor')
    def test_extract_args_parsed_and_called(self, MockGeminiExtractor):
        mock_instance = MockGeminiExtractor.return_value
        mock_instance.extract_and_save_json.return_value = Path("/tmp/fake.json")

        dummy_pdf_path = PROJECT_ROOT / "dummy_for_extract.pdf" # Use project root for temporary files if possible
        dummy_pdf_path.touch()

        self.assertEqual(self.run_main_for_test(['extract', '--pdf_file', str(dummy_pdf_path), '--output_json_dir', '/tmp/output']), 0)
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        mock_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=dummy_pdf_path,
            output_json_dir=Path('/tmp/output'),
            dry_run=False
        )
        dummy_pdf_path.unlink()

    @patch('causaganha.legalelo.pipeline.GeminiExtractor')
    def test_extract_dry_run(self, MockGeminiExtractor):
        mock_instance = MockGeminiExtractor.return_value
        mock_instance.extract_and_save_json.return_value = Path("/tmp/fake_dry.json")
        dummy_pdf_path = PROJECT_ROOT / "dummy_for_extract_dry.pdf"
        # For dry-run, file doesn't need to exist if pipeline's extract_and_save_json handles it.
        # pipeline.py's GeminiExtractor mock was updated to not require file existence on dry-run.

        self.assertEqual(self.run_main_for_test(['extract', '--pdf_file', str(dummy_pdf_path), '--dry-run']), 0)
        MockGeminiExtractor.assert_called_once_with(verbose=False) # verbose is False by default
        mock_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=dummy_pdf_path,
            output_json_dir=None,
            dry_run=True
        )

    def test_update_command(self):
        self.assertEqual(self.run_main_for_test(['update']), 0)
        self.assertIn("Update command is a placeholder", self.mock_stdout.getvalue())

    def test_update_dry_run(self):
        self.assertEqual(self.run_main_for_test(['update', '--dry-run']), 0)
        self.assertIn("DRY-RUN: Update command is a placeholder", self.mock_stdout.getvalue())

    @patch('causaganha.legalelo.pipeline.fetch_tjro_pdf')
    @patch('causaganha.legalelo.pipeline.GeminiExtractor')
    def test_run_command_orchestration(self, MockGeminiExtractor, mock_fetch):
        mock_fetch.return_value = Path("/tmp/collected_via_run.pdf")
        mock_extractor_instance = MockGeminiExtractor.return_value
        mock_extractor_instance.extract_and_save_json.return_value = Path("/tmp/extracted_via_run.json")

        self.assertEqual(self.run_main_for_test(['run', '--date', '2024-03-12']), 0)

        mock_fetch.assert_called_once_with(date_str='2024-03-12', dry_run=False, verbose=False)
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        mock_extractor_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=Path("/tmp/collected_via_run.pdf"),
            output_json_dir=None,
            dry_run=False
        )

    @patch('causaganha.legalelo.pipeline.fetch_tjro_pdf')
    @patch('causaganha.legalelo.pipeline.GeminiExtractor')
    def test_run_command_dry_run(self, MockGeminiExtractor, mock_fetch):
        mock_fetch.return_value = Path("/tmp/collected_dry_run.pdf")
        mock_extractor_instance = MockGeminiExtractor.return_value
        mock_extractor_instance.extract_and_save_json.return_value = Path("/tmp/extracted_dry_run.json")

        # When --dry-run is global, it should propagate to verbose in GeminiExtractor via run_command logic
        # and to dry_run in both fetch_tjro_pdf and extract_and_save_json
        self.assertEqual(self.run_main_for_test(['--verbose', 'run', '--date', '2024-03-13', '--dry-run']), 0)

        mock_fetch.assert_called_once_with(date_str='2024-03-13', dry_run=True, verbose=True)
        MockGeminiExtractor.assert_called_once_with(verbose=True)
        mock_extractor_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=Path("/tmp/collected_dry_run.pdf"),
            output_json_dir=None, # Default for run
            dry_run=True
        )

    def test_unknown_argument(self):
        # If a command is not provided, argparse first complains about the missing command.
        self.assertEqual(self.run_main_for_test(['--nonexistent-arg']), 2) # argparse exits with 2
        self.assertIn("the following arguments are required: command", self.mock_stderr.getvalue())

    def test_unknown_subcommand_argument(self):
        # Test an unrecognized argument for a subcommand
        self.assertEqual(self.run_main_for_test(['update', '--nonexistent-arg']), 2)
        self.assertIn("unrecognized arguments: --nonexistent-arg", self.mock_stderr.getvalue())

    def test_collect_missing_date(self):
        self.assertEqual(self.run_main_for_test(['collect']), 2)
        self.assertIn("the following arguments are required: --date", self.mock_stderr.getvalue())

    def test_extract_missing_pdf_file(self):
        self.assertEqual(self.run_main_for_test(['extract']), 2)
        self.assertIn("the following arguments are required: --pdf_file", self.mock_stderr.getvalue())

    # Test for date format - argparse itself doesn't validate YYYY-MM-DD.
    # The current pipeline's mock fetch_tjro_pdf just takes the string.
    # This test just ensures the string is passed.
    @patch('causaganha.legalelo.pipeline.fetch_tjro_pdf')
    def test_collect_invalid_date_format_passed_through(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake_invalid_date.pdf")
        self.assertEqual(self.run_main_for_test(['collect', '--date', 'NOT-A-DATE']), 0)
        mock_fetch.assert_called_once_with(date_str='NOT-A-DATE', dry_run=False, verbose=False)


    @patch('logging.basicConfig')
    def test_verbose_flag_sets_debug_level_basicConfig(self, mock_basic_config):
        self.run_main_for_test(['--verbose', 'update'])

        # Check if basicConfig was called with level=logging.DEBUG
        called_with_debug = any(
            call_args.kwargs.get('level') == logging.DEBUG
            for call_args in mock_basic_config.call_args_list
        )
        self.assertTrue(called_with_debug, "logging.basicConfig was not called with logging.DEBUG when --verbose was used.")

    @patch('logging.getLogger')
    def test_verbose_logging_capture_for_update(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        self.run_main_for_test(['--verbose', 'update'])

        # Check if logger.debug was called.
        self.assertTrue(mock_logger_instance.debug.called, "Logger's debug method was not called with --verbose.")

        # Check for a specific debug log from 'update_command'
        # (depends on the f-string content which includes the args object representation)
        self.assertTrue(
            any("Update command called with args" in str(call_arg) for call_arg in mock_logger_instance.debug.call_args_list),
            "Expected debug log from update_command not found."
        )

    @patch('logging.getLogger')
    def test_dry_run_logging_capture_for_collect(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        # We want the actual (simulated) fetch_tjro_pdf from pipeline.py to run and log.
        # So, DO NOT patch 'causaganha.legalelo.pipeline.fetch_tjro_pdf' here.
        self.run_main_for_test(['collect', '--date', '2024-01-01', '--dry-run'])

        # Check for "DRY-RUN" in info logs from the fetch_tjro_pdf in pipeline.py
        dry_run_fetch_logged = any(
            "DRY-RUN: Would fetch TJRO PDF for date: 2024-01-01" in str(call_arg)
            for call_arg in mock_logger_instance.info.call_args_list
        )
        self.assertTrue(
            dry_run_fetch_logged,
            f"Expected DRY-RUN info log from fetch_tjro_pdf not found. Actual .info() calls: {mock_logger_instance.info.call_args_list}"
        )

if __name__ == '__main__':
    # This allows running the tests directly from this file using:
    # python causaganha/tests/test_pipeline.py
    # However, it's generally better to use `python -m unittest discover` from the project root.
    unittest.main(argv=[sys.argv[0]] + sys.argv[1:], exit=False)
