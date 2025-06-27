import unittest
from unittest.mock import patch, MagicMock
import sys
from io import StringIO
import logging
from pathlib import Path

# import pandas as pd # No longer needed for these tests as pipeline.py doesn't use it directly for CSVs
import json
import argparse  # Import argparse for creating Namespace objects

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# This try-except is for local execution of this test file.
# Pytest execution should handle imports via conftest.py or pythonpath.
try:
    from src import pipeline  # Try to import the pipeline module from src
except ModuleNotFoundError:
    pipeline = None  # Will be caught by setUp methods


class TestPipelineArgParsingAndExecution(unittest.TestCase):
    def setUp(self):
        if pipeline is None:
            self.fail(
                "The 'pipeline' module (src.pipeline) could not be imported. Check PYTHONPATH or import errors."
            )

        self.stdout_patch = patch("sys.stdout", new_callable=StringIO)
        self.stderr_patch = patch("sys.stderr", new_callable=StringIO)
        self.mock_stdout = self.stdout_patch.start()
        self.mock_stderr = self.stderr_patch.start()

        # Clear and configure logging for testing purposes
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        # Configure root logger for tests to see logs from modules if needed
        logging.basicConfig(stream=self.mock_stdout, level=logging.DEBUG, force=True)

    def tearDown(self):
        self.stdout_patch.stop()
        self.stderr_patch.stop()
        # Restore default logging
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        logging.basicConfig(level=logging.WARNING, force=True)

    def run_main_for_test(self, args_list):
        original_argv = sys.argv
        try:
            sys.argv = ["pipeline_script_name_for_argparse"] + args_list
            result = pipeline.main()
            # If the command function returns a Path, it's a success
            if isinstance(result, Path):
                return 0
            # If it returns None, it's a failure
            elif result is None:
                return 1
            # Otherwise, assume it's an integer exit code
            else:
                return result
        except SystemExit as e:
            return e.code
        finally:
            sys.argv = original_argv

    @patch("src.pipeline.fetch_tjro_pdf")  # Patching where it's used
    def test_collect_args_parsed_and_called(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake.pdf")
        # Pass verbose=False explicitly as it's now added to subparsers by default in pipeline.py
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

    @patch("src.pipeline.GeminiExtractor")
    def test_extract_args_parsed_and_called(self, MockGeminiExtractor):
        mock_instance = MockGeminiExtractor.return_value
        mock_instance.extract_and_save_json.return_value = Path("/tmp/fake.json")
        dummy_pdf_path = PROJECT_ROOT / "dummy_for_extract.pdf"
        with open(dummy_pdf_path, "w") as f:
            f.write("dummy content")  # Ensure file exists

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
        dummy_pdf_path = PROJECT_ROOT / "dummy_for_extract_dry.pdf"
        with open(dummy_pdf_path, "w") as f:
            f.write("dummy content")

        self.assertEqual(
            self.run_main_for_test(
                ["extract", "--pdf_file", str(dummy_pdf_path), "--dry-run"]
            ),
            0,
        )
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        # output_json_dir defaults to pdf_file.parent
        mock_instance.extract_and_save_json.assert_called_once_with(
            pdf_path=dummy_pdf_path, output_json_dir=dummy_pdf_path.parent, dry_run=True
        )
        if dummy_pdf_path.exists():
            dummy_pdf_path.unlink()

    @patch(
        "src.pipeline._update_ratings_logic"
    )  # Patch the direct function called by run_command
    @patch(
        "src.pipeline.extract_command"
    )  # Patch the command function called by run_command
    @patch(
        "src.pipeline.collect_command"
    )  # Patch the command function called by run_command
    def test_run_command_orchestration(
        self, mock_collect_cmd, mock_extract_cmd, mock_update_logic
    ):
        mock_collect_cmd.return_value = Path("/tmp/collected_via_run.pdf")
        mock_extract_cmd.return_value = (
            PROJECT_ROOT / "data" / "json" / "run_extracted.json"
        )

        # Mock CausaGanhaDB and PiiManager as they are instantiated in run_command for _update_ratings_logic
        with (
            patch("src.pipeline.CausaGanhaDB") as MockCausaGanhaDB,
            patch("src.pipeline.PiiManager") as MockPiiManager,
        ):
            MockPiiManager.return_value  # consume return value

            self.assertEqual(self.run_main_for_test(["run", "--date", "2024-03-12"]), 0)

            mock_collect_cmd.assert_called_once()
            # Check specific args passed to collect_command's Namespace
            self.assertEqual(mock_collect_cmd.call_args[0][0].date, "2024-03-12")
            self.assertFalse(mock_collect_cmd.call_args[0][0].dry_run)
            self.assertFalse(mock_collect_cmd.call_args[0][0].verbose)

            mock_extract_cmd.assert_called_once()
            self.assertEqual(
                mock_extract_cmd.call_args[0][0].pdf_file,
                Path("/tmp/collected_via_run.pdf"),
            )
            self.assertFalse(mock_extract_cmd.call_args[0][0].dry_run)

            mock_update_logic.assert_called_once()
            # Check args passed to _update_ratings_logic
            self.assertFalse(mock_update_logic.call_args[0][1])  # dry_run
            self.assertIsInstance(
                mock_update_logic.call_args[0][2], MockCausaGanhaDB
            )  # db instance
            self.assertIsInstance(
                mock_update_logic.call_args[0][3], MockPiiManager
            )  # pii_manager instance

    @patch("src.pipeline._update_ratings_logic")
    @patch("src.pipeline.extract_command")
    @patch("src.pipeline.collect_command")
    def test_run_command_dry_run(
        self, mock_collect_cmd, mock_extract_cmd, mock_update_logic
    ):
        mock_collect_cmd.return_value = Path("/tmp/collected_dry_run.pdf")
        mock_extract_cmd.return_value = (
            PROJECT_ROOT / "data" / "json" / "run_extracted_dry.json"
        )

        with patch("src.pipeline.CausaGanhaDB"), patch("src.pipeline.PiiManager"):
            self.assertEqual(
                self.run_main_for_test(
                    ["run", "--date", "2024-03-13", "--dry-run", "--verbose"]
                ),
                0,
            )

        mock_collect_cmd.assert_called_once()
        self.assertTrue(mock_collect_cmd.call_args[0][0].dry_run)
        self.assertTrue(mock_collect_cmd.call_args[0][0].verbose)

        mock_extract_cmd.assert_called_once()
        self.assertTrue(mock_extract_cmd.call_args[0][0].dry_run)

        mock_update_logic.assert_called_once()
        self.assertTrue(
            mock_update_logic.call_args[0][1]
        )  # dry_run for _update_ratings_logic

    def test_unknown_argument(self):
        self.assertEqual(self.run_main_for_test(["update", "--nonexistent-arg"]), 2)
        self.assertIn(
            "unrecognized arguments: --nonexistent-arg", self.mock_stderr.getvalue()
        )

    def test_unknown_subcommand_argument(self):
        self.assertEqual(
            self.run_main_for_test(
                ["update", "--nonexistent-arg", "--verbose", "False"]
            ),
            2,
        )
        self.assertIn(
            "unrecognized arguments: --nonexistent-arg", self.mock_stderr.getvalue()
        )

    def test_collect_missing_date(self):
        self.assertEqual(self.run_main_for_test(["collect", "--verbose", "False"]), 2)
        self.assertIn(
            "the following arguments are required: --date", self.mock_stderr.getvalue()
        )

    def test_extract_missing_pdf_file(self):
        self.assertEqual(self.run_main_for_test(["extract", "--verbose", "False"]), 2)
        self.assertIn(
            "the following arguments are required: --pdf_file",
            self.mock_stderr.getvalue(),
        )

    @patch("src.pipeline.fetch_tjro_pdf")
    def test_collect_invalid_date_format_passed_through(self, mock_fetch):
        mock_fetch.return_value = Path(
            "/tmp/fake_invalid_date.pdf"
        )  # fetch_tjro_pdf itself handles date parsing now
        self.assertEqual(self.run_main_for_test(["collect", "--date", "NOT-A-DATE"]), 0)
        mock_fetch.assert_called_once_with(
            date_str="NOT-A-DATE", dry_run=False, verbose=False
        )

    @patch("logging.basicConfig")
    def test_verbose_flag_sets_debug_level_basicConfig(self, mock_basic_config):
        with patch.object(pipeline, "update_command", MagicMock()):
            self.run_main_for_test(["update"])

        debug_level_set = False
        for call_args_tuple in mock_basic_config.call_args_list:
            if call_args_tuple.kwargs.get("level") == logging.DEBUG:
                debug_level_set = True
                break
        self.assertTrue(
            debug_level_set,
            "logging.basicConfig was not called with logging.DEBUG. Calls: "
            + str(mock_basic_config.call_args_list),
        )

    @patch("logging.getLogger")
    def test_verbose_logging_capture_for_update(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        # Patch the actual logic function that update_command calls
        with patch.object(pipeline, "_update_ratings_logic", MagicMock()):
            self.run_main_for_test(["update"])  # Pass --verbose to update sub-command

        # Check if the logger for 'pipeline' (used in update_command) was called with debug
        debug_call_found = False
        for call in mock_logger_instance.debug.call_args_list:
            if "Update command called with args" in str(call[0][0]):
                debug_call_found = True
                break
        self.assertTrue(
            debug_call_found,
            "Logger debug was not called with expected message for update command.",
        )

    @patch("logging.getLogger")
    def test_dry_run_logging_capture_for_collect(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        with patch(
            "src.pipeline.fetch_tjro_pdf", MagicMock(return_value=Path("fake.pdf"))
        ):  # Mock actual fetch
            self.run_main_for_test(["collect", "--date", "2024-01-01", "--dry-run"])

        dry_run_fetch_logged = any(
            "Collect successful. PDF: fake.pdf" in str(call_arg)
            for call_arg in mock_logger_instance.info.call_args_list
        )
        self.assertTrue(
            dry_run_fetch_logged,
            f"Expected 'Collect successful' info log not found. Actual: {mock_logger_instance.info.call_args_list}",
        )


class TestPipelineUpdateCommand(unittest.TestCase):
    # This class needs significant refactoring to mock DB and PII manager
    # instead of CSV operations.
    def setUp(self):
        if pipeline is None:
            self.fail("The 'pipeline' module (src.pipeline) could not be imported.")

        # Create dummy JSON files for processing
        self.project_root_dir = Path(__file__).resolve().parent.parent
        self.json_input_dir = self.project_root_dir / "data" / "json"
        self.json_input_dir.mkdir(parents=True, exist_ok=True)
        self.processed_json_dir = self.project_root_dir / "data" / "json_processed"
        self.processed_json_dir.mkdir(parents=True, exist_ok=True)

        self.sample_decision_1 = {
            "numero_processo": "0000001-11.2023.8.22.0001",  # Validated format
            "advogados_polo_ativo": ["AdvA"],
            "advogados_polo_passivo": ["AdvB"],
            "resultado": "procedente",
            "polo_ativo": ["PA"],
            "polo_passivo": ["PB"],
            "data_decisao": "2023-01-01",
        }
        self.sample_decision_2 = {
            "numero_processo": "0000002-22.2023.8.22.0002",  # Validated format
            "advogados_polo_ativo": ["AdvC"],
            "advogados_polo_passivo": ["AdvA"],
            "resultado": "improcedente",
            "polo_ativo": ["PC"],
            "polo_passivo": ["PD"],
            "data_decisao": "2023-01-02",
        }

        with open(self.json_input_dir / "decision1.json", "w") as f:
            json.dump(
                {
                    "decisions": [self.sample_decision_1],
                    "file_name_source": "decision1.pdf",
                },
                f,
            )
        with open(self.json_input_dir / "decision2.json", "w") as f:
            json.dump(
                {
                    "decisions": [self.sample_decision_2],
                    "file_name_source": "decision2.pdf",
                },
                f,
            )

        # Capture logs
        self.log_capture_string = StringIO()
        self.pipeline_logger = logging.getLogger(
            "pipeline"
        )  # Logger used in pipeline.py
        self.ch = logging.StreamHandler(self.log_capture_string)
        self.pipeline_logger.addHandler(self.ch)
        self.pipeline_logger.setLevel(logging.INFO)

    def tearDown(self):
        self.pipeline_logger.removeHandler(self.ch)
        for f_name in ["decision1.json", "decision2.json"]:
            if (self.json_input_dir / f_name).exists():
                (self.json_input_dir / f_name).unlink()
            if (self.processed_json_dir / f_name).exists():
                (self.processed_json_dir / f_name).unlink()
        if self.json_input_dir.exists() and not any(self.json_input_dir.iterdir()):
            self.json_input_dir.rmdir()
        if self.processed_json_dir.exists() and not any(
            self.processed_json_dir.iterdir()
        ):
            self.processed_json_dir.rmdir()
        # Clean data dir if empty
        data_dir = self.project_root_dir / "data"
        if data_dir.exists() and not any(data_dir.iterdir()):
            data_dir.rmdir()

    @patch("src.pipeline.shutil.move")
    @patch("src.pipeline.PiiManager")
    @patch("src.pipeline.CausaGanhaDB")
    def test_update_command_valid_decisions(
        self, MockCausaGanhaDB, MockPiiManager, mock_shutil_move
    ):
        mock_db_instance = MockCausaGanhaDB.return_value
        mock_pii_instance = MockPiiManager.return_value

        # Simulate PII mapping
        def pii_map_side_effect(val, ptype, norm_val=None):
            return f"uuid_for_{norm_val or val}_{ptype}"

        mock_pii_instance.get_or_create_pii_mapping.side_effect = pii_map_side_effect

        # Simulate DB get_rating (player not found initially)
        mock_db_instance.get_rating.return_value = None

        args = argparse.Namespace(
            dry_run=False, verbose=False
        )  # Explicitly set verbose for command
        pipeline.update_command(args)

        MockCausaGanhaDB.assert_called_once()
        MockPiiManager.assert_called_once_with(mock_db_instance.conn)

        self.assertTrue(mock_pii_instance.get_or_create_pii_mapping.called)
        self.assertTrue(mock_db_instance.add_raw_decision.called)
        self.assertTrue(mock_db_instance.get_rating.called)
        self.assertTrue(mock_db_instance.update_rating.called)
        self.assertTrue(mock_db_instance.add_partida.called)

        # Two files should be moved
        self.assertEqual(mock_shutil_move.call_count, 2)

    @patch("src.pipeline.shutil.move")
    @patch("src.pipeline.PiiManager")
    @patch("src.pipeline.CausaGanhaDB")
    def test_update_command_dry_run(
        self, MockCausaGanhaDB, MockPiiManager, mock_shutil_move
    ):
        mock_db_instance = MockCausaGanhaDB.return_value
        mock_pii_instance = MockPiiManager.return_value
        mock_pii_instance.get_or_create_pii_mapping.side_effect = (
            lambda val, ptype, norm_val: f"uuid_for_{norm_val or val}_{ptype}"
        )
        mock_db_instance.get_rating.return_value = None

        args = argparse.Namespace(dry_run=True, verbose=False)
        pipeline.update_command(args)

        mock_db_instance.add_raw_decision.assert_not_called()
        mock_db_instance.update_rating.assert_not_called()
        mock_db_instance.add_partida.assert_not_called()
        mock_shutil_move.assert_not_called()

        self.assertTrue(mock_pii_instance.get_or_create_pii_mapping.called)
        self.assertTrue(mock_db_instance.get_rating.called)

    @patch(
        "src.pipeline.validate_decision", return_value=False
    )  # Make all decisions invalid
    @patch("src.pipeline.shutil.move")
    @patch("src.pipeline.PiiManager")
    @patch("src.pipeline.CausaGanhaDB")
    def test_update_command_all_decisions_invalid(
        self, MockCausaGanhaDB, MockPiiManager, mock_shutil_move, mock_validate_decision
    ):
        mock_db_instance = MockCausaGanhaDB.return_value

        args = argparse.Namespace(dry_run=False, verbose=False)
        pipeline.update_command(args)

        mock_db_instance.add_raw_decision.assert_not_called()
        mock_db_instance.update_rating.assert_not_called()
        mock_db_instance.add_partida.assert_not_called()
        mock_shutil_move.assert_not_called()
        self.assertTrue(mock_validate_decision.call_count >= 2)


if __name__ == "__main__":
    # This part is for running tests directly via `python tests/test_pipeline.py`
    # Pytest will use its own collection and execution mechanisms.
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG,
        format="%(name)s - %(levelname)s - %(message)s",
    )
    unittest.main(argv=sys.argv[:1], verbosity=2, exit=False)
