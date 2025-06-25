import unittest
from unittest.mock import patch, MagicMock
import sys
from io import StringIO
import logging
from pathlib import Path
import pandas as pd  # For pipeline update tests
import json  # For creating dummy json files

# Add project root to sys.path to allow importing causaganha
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Attempt to import the module under test
try:
    from causaganha.core import pipeline

    # Also import specific items that might be patched or referred to
    from causaganha.core.utils import normalize_lawyer_name, validate_decision
    from causaganha.core.elo import update_elo
except ModuleNotFoundError as e:
    print(
        f"ERROR: Could not import causaganha.core modules. Original error: {e}",
        file=sys.stderr,
    )
    pipeline = None

# Suppress most logging during tests, enable for specific test debugging if needed
# logging.disable(logging.CRITICAL) # Can be too broad, let specific tests manage if needed.


class TestPipelineArgParsingAndExecution(unittest.TestCase):
    def setUp(self):
        if pipeline is None:
            self.fail(
                "The 'pipeline' module from 'causaganha.core' could not be imported."
            )

        self.stdout_patch = patch("sys.stdout", new_callable=StringIO)
        self.stderr_patch = patch("sys.stderr", new_callable=StringIO)
        self.mock_stdout = self.stdout_patch.start()
        self.mock_stderr = self.stderr_patch.start()

        # Reset logging handlers to ensure a clean state
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        pipeline_module_logger = logging.getLogger("causaganha.core.pipeline")
        for handler in pipeline_module_logger.handlers[:]:
            pipeline_module_logger.removeHandler(handler)
        pipeline_module_logger.setLevel(logging.NOTSET)
        # Apply a null handler to the root logger to prevent "No handler found" warnings
        # if code logs before basicConfig is called by pipeline.main
        logging.getLogger().addHandler(logging.NullHandler())

    def tearDown(self):
        self.stdout_patch.stop()
        self.stderr_patch.stop()
        logging.getLogger().handlers.clear()  # Clear any handlers added during test

    def run_main_for_test(self, args_list):
        original_argv = sys.argv
        try:
            sys.argv = ["pipeline.py"] + args_list
            pipeline.main()
            return 0
        except SystemExit as e:
            return e.code
        finally:
            sys.argv = original_argv

    # ... [previous tests from TestPipelineArgParsingAndExecution remain here] ...
    # (ensure they are not duplicated if this block is appended)

    @patch("causaganha.core.pipeline.fetch_tjro_pdf")
    def test_collect_args_parsed_and_called(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake.pdf")
        self.assertEqual(self.run_main_for_test(["collect", "--date", "2024-03-10"]), 0)
        mock_fetch.assert_called_once_with(
            date_str="2024-03-10", dry_run=False, verbose=False
        )

    @patch("causaganha.core.pipeline.fetch_tjro_pdf")
    def test_collect_dry_run(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake_dry.pdf")
        self.assertEqual(
            self.run_main_for_test(["collect", "--date", "2024-03-11", "--dry-run"]), 0
        )
        mock_fetch.assert_called_once_with(
            date_str="2024-03-11", dry_run=True, verbose=False
        )

    @patch("causaganha.core.pipeline.GeminiExtractor")
    def test_extract_args_parsed_and_called(self, MockGeminiExtractor):
        mock_instance = MockGeminiExtractor.return_value
        mock_instance.extract_and_save_json.return_value = Path("/tmp/fake.json")

        dummy_pdf_path = PROJECT_ROOT / "dummy_for_extract.pdf"
        dummy_pdf_path.touch()

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

    @patch("causaganha.core.pipeline.GeminiExtractor")
    def test_extract_dry_run(self, MockGeminiExtractor):
        mock_instance = MockGeminiExtractor.return_value
        mock_instance.extract_and_save_json.return_value = Path("/tmp/fake_dry.json")
        dummy_pdf_path = PROJECT_ROOT / "dummy_for_extract_dry.pdf"

        self.assertEqual(
            self.run_main_for_test(
                ["extract", "--pdf_file", str(dummy_pdf_path), "--dry-run"]
            ),
            0,
        )
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        mock_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=dummy_pdf_path,
            output_json_dir=dummy_pdf_path.parent,  # Default output_dir for extract command
            dry_run=True,
        )

    # test_update_command and test_update_dry_run are now superseded by TestPipelineUpdateCommand
    # def test_update_command(self): ...
    # def test_update_dry_run(self): ...

    @patch(
        "causaganha.core.pipeline.update_command"
    )  # Mock update_command itself for this orchestration test
    @patch("causaganha.core.pipeline.GeminiExtractor")
    @patch("causaganha.core.pipeline.fetch_tjro_pdf")
    def test_run_command_orchestration(
        self, mock_fetch, MockGeminiExtractor, mock_update_cmd
    ):
        mock_fetch.return_value = Path("/tmp/collected_via_run.pdf")
        mock_extractor_instance = MockGeminiExtractor.return_value
        # Ensure extract_and_save_json returns a Path for the next step if needed
        mock_extractor_instance.extract_and_save_json.return_value = Path(
            "causaganha/data/json/run_extracted.json"
        )

        self.assertEqual(self.run_main_for_test(["run", "--date", "2024-03-12"]), 0)

        mock_fetch.assert_called_once_with(
            date_str="2024-03-12", dry_run=False, verbose=False
        )
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        mock_extractor_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=Path("/tmp/collected_via_run.pdf"),
            output_json_dir=Path(
                "causaganha/data/json/"
            ),  # Default for run command's extract step
            dry_run=False,
        )
        mock_update_cmd.assert_called_once()

    @patch("causaganha.core.pipeline.update_command")
    @patch("causaganha.core.pipeline.GeminiExtractor")
    @patch("causaganha.core.pipeline.fetch_tjro_pdf")
    def test_run_command_dry_run(
        self, mock_fetch, MockGeminiExtractor, mock_update_cmd
    ):
        mock_fetch.return_value = Path("/tmp/collected_dry_run.pdf")
        mock_extractor_instance = MockGeminiExtractor.return_value
        mock_extractor_instance.extract_and_save_json.return_value = Path(
            "causaganha/data/json/run_extracted_dry.json"
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
            output_json_dir=Path("causaganha/data/json/"),
            dry_run=True,
        )
        mock_update_cmd.assert_called_once()
        # Check that args passed to mock_update_cmd's call had dry_run=True
        self.assertTrue(mock_update_cmd.call_args[0][0].dry_run)

    def test_unknown_argument(self):
        self.assertEqual(self.run_main_for_test(["--nonexistent-arg"]), 2)
        self.assertIn(
            "the following arguments are required: command", self.mock_stderr.getvalue()
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

    @patch("causaganha.core.pipeline.fetch_tjro_pdf")
    def test_collect_invalid_date_format_passed_through(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake_invalid_date.pdf")
        self.assertEqual(self.run_main_for_test(["collect", "--date", "NOT-A-DATE"]), 0)
        mock_fetch.assert_called_once_with(
            date_str="NOT-A-DATE", dry_run=False, verbose=False
        )

    @patch("logging.basicConfig")
    def test_verbose_flag_sets_debug_level_basicConfig(self, mock_basic_config):
        # In update_command, the placeholder print will still occur
        # We just check that basicConfig is called with DEBUG level by setup_logging
        with patch.object(
            pipeline, "_update_elo_ratings_logic", MagicMock()
        ):  # Mock out the actual logic
            self.run_main_for_test(["--verbose", "update"])

        called_with_debug = any(
            call_args.kwargs.get("level") == logging.DEBUG
            for call_args in mock_basic_config.call_args_list
        )
        self.assertTrue(
            called_with_debug,
            "logging.basicConfig was not called with logging.DEBUG when --verbose was used.",
        )

    @patch("logging.getLogger")
    def test_verbose_logging_capture_for_update(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        with patch.object(
            pipeline, "_update_elo_ratings_logic", MagicMock()
        ):  # Mock out the actual logic
            self.run_main_for_test(["--verbose", "update"])

        self.assertTrue(mock_logger_instance.debug.called)
        self.assertTrue(
            any(
                "Update command called with args" in str(arg_call)
                for arg_call in mock_logger_instance.debug.call_args_list
            )
        )

    @patch("logging.getLogger")
    def test_dry_run_logging_capture_for_collect(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        self.run_main_for_test(["collect", "--date", "2024-01-01", "--dry-run"])

        dry_run_fetch_logged = any(
            "DRY-RUN: Would fetch TJRO PDF for date: 2024-01-01" in str(call_arg)
            for call_arg in mock_logger_instance.info.call_args_list
        )
        self.assertTrue(
            dry_run_fetch_logged,
            f"Expected DRY-RUN info log from fetch_tjro_pdf not found. Actual .info() calls: {mock_logger_instance.info.call_args_list}",
        )


# New Test Class for Update Command Logic
class TestPipelineUpdateCommand(unittest.TestCase):
    def setUp(self):
        if pipeline is None:
            self.fail(
                "The 'pipeline' module from 'causaganha.core' could not be imported."
            )

        # Define paths based on where the pipeline script actually looks for data
        self.base_data_path = PROJECT_ROOT / "causaganha" / "data"
        self.json_input_dir = self.base_data_path / "json"
        self.processed_json_dir = self.base_data_path / "json_processed"
        self.ratings_csv_path = self.base_data_path / "ratings.csv"
        self.partidas_csv_path = self.base_data_path / "partidas.csv"

        # Create these directories for the test
        self.json_input_dir.mkdir(parents=True, exist_ok=True)
        self.processed_json_dir.mkdir(parents=True, exist_ok=True)
        # self.base_data_path.mkdir(parents=True, exist_ok=True) # Covered by json_input_dir

        # No longer patching module-level path variables as they are local in the function.
        # Tests will rely on the default paths used in _update_elo_ratings_logic.

        # Dummy JSON file content
        self.sample_decision_1 = {
            "numero_processo": "0000001-01.2023.8.22.0001",
            "tipo_decisao": "sentença",
            "partes": {
                "requerente": ["Adv A Teste (OAB/UF 111)"],
                "requerido": ["Adv B Teste (OAB/UF 222)"],
            },
            "advogados": {
                "requerente": ["Adv A Teste (OAB/UF 111)"],
                "requerido": ["Adv B Teste (OAB/UF 222)"],
            },
            "resultado": "procedente",
            "data_decisao": "2023-01-01",
        }
        self.sample_decision_2 = {
            "numero_processo": "0000002-02.2023.8.22.0001",
            "tipo_decisao": "sentença",
            "partes": {
                "requerente": ["Adv C Teste (OAB/UF 333)"],
                "requerido": ["Adv A Teste (OAB/UF 111)"],
            },
            "advogados": {
                "requerente": ["Adv C Teste (OAB/UF 333)"],
                "requerido": ["Adv A Teste (OAB/UF 111)"],
            },
            "resultado": "improcedente",
            "data_decisao": "2023-01-02",
        }
        with open(self.json_input_dir / "decision1.json", "w") as f:
            json.dump([self.sample_decision_1], f)  # Store as a list of one
        with open(self.json_input_dir / "decision2.json", "w") as f:
            json.dump([self.sample_decision_2], f)

        # Initial ratings CSV (optional, can be empty)
        # Corrected to use self.base_data_path as self.data_dir is no longer defined.
        self.ratings_csv_path = self.base_data_path / "ratings.csv"
        self.partidas_csv_path = self.base_data_path / "partidas.csv"
        # Create empty ratings file or with some initial data
        pd.DataFrame(columns=["advogado_id", "rating", "total_partidas"]).set_index(
            "advogado_id"
        ).to_csv(self.ratings_csv_path)
        # Ensure partidas.csv does not exist initially or is empty if that's the expectation
        if self.partidas_csv_path.exists():
            self.partidas_csv_path.unlink()

        # Suppress stdout/stderr for cleaner test logs
        self.stdout_patch = patch("sys.stdout", new_callable=StringIO)
        self.stderr_patch = patch("sys.stderr", new_callable=StringIO)
        self.mock_stdout = self.stdout_patch.start()
        self.mock_stderr = self.stderr_patch.start()

        # Apply a null handler to the root logger to prevent "No handler found" warnings
        # if code logs before basicConfig is called by pipeline.main
        logging.getLogger().addHandler(logging.NullHandler())

    def tearDown(self):
        # No patches to stop for paths anymore.
        # Clean up files and directories created in the actual data paths.
        if self.json_input_dir.exists():
            for f in self.json_input_dir.glob("*.json"):  # remove only test jsons
                if f.name.startswith("decision"):  # or specific names used in tests
                    f.unlink()
            # Potentially rmdir if empty and owned by test, but be careful
        if self.processed_json_dir.exists():
            for f in self.processed_json_dir.glob("*.json"):
                if f.name.startswith("decision"):
                    f.unlink()
        if self.ratings_csv_path.exists():
            self.ratings_csv_path.unlink()
        if self.partidas_csv_path.exists():
            self.partidas_csv_path.unlink()
        # Careful with shutil.rmtree on actual data paths unless they were fully created by test
        # For now, specific file cleanup is safer.

        self.stdout_patch.stop()
        self.stderr_patch.stop()
        logging.getLogger().handlers.clear()

    @patch("causaganha.core.pipeline.shutil.move")
    @patch("causaganha.core.pipeline.pd.DataFrame.to_csv")
    @patch(
        "causaganha.core.pipeline.pd.read_csv"
    )  # Patching pandas at the pipeline module level
    def test_update_command_valid_decisions(
        self, mock_read_csv, mock_to_csv, mock_shutil_move
    ):
        # Mock initial ratings
        initial_ratings_df = pd.DataFrame(
            columns=["advogado_id", "rating", "total_partidas"]
        ).set_index("advogado_id")
        mock_read_csv.return_value = initial_ratings_df

        # Run the update command (not dry run) by simulating how main() would call it
        # Need to use the run_main_for_test helper or ensure logging is set up if calling directly
        # For simplicity, let's create args and call the command function directly.
        # Logging setup would typically be done by main(), so for direct call, ensure logger works.
        logging.basicConfig(
            level=logging.DEBUG, stream=sys.stderr
        )  # Ensure logs are visible for test debug
        args = pipeline.argparse.Namespace(
            dry_run=False, verbose=True
        )  # Simulate parsed args

        # The pipeline.update_command calls _update_elo_ratings_logic
        # We are testing this integrated call.
        pipeline.update_command(args)

        # Assertions
        # _update_elo_ratings_logic uses Path('causaganha/data/ratings.csv')
        mock_read_csv.assert_called_once_with(
            Path("causaganha/data/ratings.csv"), index_col="advogado_id"
        )

        # Two to_csv calls: one for ratings, one for partidas
        self.assertEqual(mock_to_csv.call_count, 2)

        # Check ratings_df content (harder to check exact df, check for key players)
        # The first call to to_csv is ratings_df.to_csv(ratings_file)
        # The second call is partidas_df.to_csv(partidas_file, index=False)

        # Check shutil.move calls - two files should be moved
        self.assertEqual(mock_shutil_move.call_count, 2)
        # _update_elo_ratings_logic calls shutil.move with stringified relative paths
        mock_shutil_move.assert_any_call(
            str(Path("causaganha/data/json/decision1.json")),
            str(Path("causaganha/data/json_processed/decision1.json")),
        )
        mock_shutil_move.assert_any_call(
            str(Path("causaganha/data/json/decision2.json")),
            str(Path("causaganha/data/json_processed/decision2.json")),
        )

        # Verify content of ratings DataFrame passed to to_csv
        # This requires capturing the DataFrame passed to the first mock_to_csv call
        # ratings_df_saved = mock_to_csv.call_args_list[0][0][0] # This is complex to get the df instance
        # For simplicity, we trust the Elo logic (tested elsewhere) and focus on calls.

        # Check that partidas_df was created and saved
        # partidas_df_saved = mock_to_csv.call_args_list[1][0][0]
        # self.assertEqual(len(partidas_df_saved), 2) # Two matches processed

    @patch("causaganha.core.pipeline.shutil.move")
    @patch("causaganha.core.pipeline.pd.DataFrame.to_csv")
    @patch("causaganha.core.pipeline.pd.read_csv")
    def test_update_command_dry_run(self, mock_read_csv, mock_to_csv, mock_shutil_move):
        initial_ratings_df = pd.DataFrame(
            columns=["advogado_id", "rating", "total_partidas"]
        ).set_index("advogado_id")
        mock_read_csv.return_value = initial_ratings_df

        logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
        args = pipeline.argparse.Namespace(dry_run=True, verbose=True)
        pipeline.update_command(args)

        mock_read_csv.assert_called_once_with(
            Path("causaganha/data/ratings.csv"), index_col="advogado_id"
        )
        mock_to_csv.assert_not_called()  # Does not write files
        mock_shutil_move.assert_not_called()  # Does not move files

    @patch(
        "causaganha.core.pipeline.validate_decision", return_value=False
    )  # All decisions invalid
    @patch("causaganha.core.pipeline.shutil.move")
    @patch("causaganha.core.pipeline.pd.DataFrame.to_csv")
    @patch("causaganha.core.pipeline.pd.read_csv")
    def test_update_command_all_decisions_invalid(
        self, mock_read_csv, mock_to_csv, mock_shutil_move, mock_validate
    ):
        initial_ratings_df = pd.DataFrame(
            {
                "advogado_id": ["adv x (oab/xx 000)"],
                "rating": [1500.0],
                "total_partidas": [0],
            }
        ).set_index("advogado_id")
        mock_read_csv.return_value = initial_ratings_df

        logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
        args = pipeline.argparse.Namespace(dry_run=False, verbose=True)
        pipeline.update_command(args)

        # Ratings read. If it was not empty, it's saved.
        # If ratings_df is not empty (e.g. from load), it will be saved.
        self.assertEqual(
            mock_to_csv.call_count, 1
        )  # ratings.csv (potentially empty or initial)

        # No partidas should be generated or saved
        # The logic saves partidas_df only if partidas_history is non-empty.
        # Check that the second call (partidas) did not happen, or if it did, it was with an empty df.
        # This depends on how we check calls for pandas specifically.
        # For now, assuming only ratings.csv save if no partidas.

        mock_shutil_move.assert_not_called()  # No files processed successfully to be moved.
        self.assertTrue(
            mock_validate.call_count >= 2
        )  # Called for decisions in both files


if __name__ == "__main__":
    # This structure allows running all tests in this file using:
    # python -m unittest causaganha.tests.test_pipeline
    # Or, if you add specific test loader logic here.
    # For now, ensure logging is not disabled when running directly for debugging.
    logging.disable(logging.NOTSET)
    logging.basicConfig(
        level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s"
    )

    # Create a TestSuite
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPipelineArgParsingAndExecution))
    suite.addTest(unittest.makeSuite(TestPipelineUpdateCommand))

    # Run the TestSuite
    # runner = unittest.TextTestRunner(verbosity=2)
    # runner.run(suite)
    # Simpler: just run main, it will discover both classes if TestLoader's default behavior is used.
    unittest.main(argv=["first-arg-is-ignored"], verbosity=2, exit=False)
