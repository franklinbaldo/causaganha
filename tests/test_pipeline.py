import unittest
from unittest.mock import patch, MagicMock
import sys
from io import StringIO
import logging
from pathlib import Path
import pandas as pd
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

try:
    import pipeline
except ModuleNotFoundError as e:
    print(f"ERROR: Could not import modules. Original error: {e}", file=sys.stderr)
    pipeline = None

class TestPipelineArgParsingAndExecution(unittest.TestCase):
    def setUp(self):
        if pipeline is None:
            self.fail("The 'pipeline' module could not be imported.")
        self.stdout_patch = patch("sys.stdout", new_callable=StringIO)
        self.stderr_patch = patch("sys.stderr", new_callable=StringIO)
        self.mock_stdout = self.stdout_patch.start()
        self.mock_stderr = self.stderr_patch.start()
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]: root_logger.removeHandler(handler)
        pipeline_module_logger = logging.getLogger("pipeline")
        for handler in pipeline_module_logger.handlers[:]: pipeline_module_logger.removeHandler(handler)
        pipeline_module_logger.setLevel(logging.NOTSET)
        logging.getLogger().addHandler(logging.NullHandler())

    def tearDown(self):
        self.stdout_patch.stop()
        self.stderr_patch.stop()
        logging.getLogger().handlers.clear()

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

    @patch("pipeline.fetch_tjro_pdf")
    def test_collect_args_parsed_and_called(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake.pdf")
        self.assertEqual(self.run_main_for_test(["collect", "--date", "2024-03-10"]), 0)
        mock_fetch.assert_called_once_with(date_str="2024-03-10", dry_run=False, verbose=False)

    @patch("pipeline.fetch_tjro_pdf")
    def test_collect_dry_run(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake_dry.pdf")
        self.assertEqual(self.run_main_for_test(["collect", "--date", "2024-03-11", "--dry-run"]), 0)
        mock_fetch.assert_called_once_with(date_str="2024-03-11", dry_run=True, verbose=False)

    @patch("pipeline.GeminiExtractor")
    def test_extract_args_parsed_and_called(self, MockGeminiExtractor):
        mock_instance = MockGeminiExtractor.return_value
        mock_instance.extract_and_save_json.return_value = Path("/tmp/fake.json")
        dummy_pdf_path = PROJECT_ROOT / "dummy_for_extract.pdf"; dummy_pdf_path.touch()
        self.assertEqual(self.run_main_for_test(["extract", "--pdf_file", str(dummy_pdf_path), "--output_json_dir", "/tmp/output"]),0,)
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        mock_instance.extract_and_save_json.assert_called_once_with(pdf_path=dummy_pdf_path, output_json_dir=Path("/tmp/output"), dry_run=False)
        if dummy_pdf_path.exists(): dummy_pdf_path.unlink()

    @patch("pipeline.GeminiExtractor")
    def test_extract_dry_run(self, MockGeminiExtractor):
        mock_instance = MockGeminiExtractor.return_value
        mock_instance.extract_and_save_json.return_value = Path("/tmp/fake_dry.json")
        dummy_pdf_path = PROJECT_ROOT / "dummy_for_extract_dry.pdf"
        self.assertEqual(self.run_main_for_test(["extract", "--pdf_file", str(dummy_pdf_path), "--dry-run"]),0,)
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        mock_instance.extract_and_save_json.assert_called_once_with(pdf_path=dummy_pdf_path, output_json_dir=dummy_pdf_path.parent, dry_run=True)

    @patch("pipeline.update_command")
    @patch("pipeline.GeminiExtractor")
    @patch("pipeline.fetch_tjro_pdf")
    def test_run_command_orchestration(self, mock_fetch, MockGeminiExtractor, mock_update_cmd):
        mock_fetch.return_value = Path("/tmp/collected_via_run.pdf")
        mock_extractor_instance = MockGeminiExtractor.return_value
        mock_extractor_instance.extract_and_save_json.return_value = Path("causaganha/data/json/run_extracted.json")
        self.assertEqual(self.run_main_for_test(["run", "--date", "2024-03-12"]), 0)
        mock_fetch.assert_called_once_with(date_str="2024-03-12", dry_run=False, verbose=False)
        MockGeminiExtractor.assert_called_once_with(verbose=False)
        mock_extractor_instance.extract_and_save_json.assert_called_once_with(pdf_path=Path("/tmp/collected_via_run.pdf"), output_json_dir=Path("causaganha/data/json/"), dry_run=False)
        mock_update_cmd.assert_called_once()

    @patch("pipeline.update_command")
    @patch("pipeline.GeminiExtractor")
    @patch("pipeline.fetch_tjro_pdf")
    def test_run_command_dry_run(self, mock_fetch, MockGeminiExtractor, mock_update_cmd):
        mock_fetch.return_value = Path("/tmp/collected_dry_run.pdf")
        mock_extractor_instance = MockGeminiExtractor.return_value
        mock_extractor_instance.extract_and_save_json.return_value = Path("causaganha/data/json/run_extracted_dry.json")
        self.assertEqual(self.run_main_for_test(["--verbose", "run", "--date", "2024-03-13", "--dry-run"]),0,)
        mock_fetch.assert_called_once_with(date_str="2024-03-13", dry_run=True, verbose=True)
        MockGeminiExtractor.assert_called_once_with(verbose=True)
        mock_extractor_instance.extract_and_save_json.assert_called_once_with(pdf_path=Path("/tmp/collected_dry_run.pdf"), output_json_dir=Path("causaganha/data/json/"), dry_run=True)
        mock_update_cmd.assert_called_once()
        self.assertTrue(mock_update_cmd.call_args[0][0].dry_run)

    def test_unknown_argument(self):
        self.assertEqual(self.run_main_for_test(["--nonexistent-arg"]), 2)
        self.assertIn("the following arguments are required: command", self.mock_stderr.getvalue())

    def test_unknown_subcommand_argument(self):
        self.assertEqual(self.run_main_for_test(["update", "--nonexistent-arg"]), 2)
        self.assertIn("unrecognized arguments: --nonexistent-arg", self.mock_stderr.getvalue())

    def test_collect_missing_date(self):
        self.assertEqual(self.run_main_for_test(["collect"]), 2)
        self.assertIn("the following arguments are required: --date", self.mock_stderr.getvalue())

    def test_extract_missing_pdf_file(self):
        self.assertEqual(self.run_main_for_test(["extract"]), 2)
        self.assertIn("the following arguments are required: --pdf_file", self.mock_stderr.getvalue())

    @patch("pipeline.fetch_tjro_pdf")
    def test_collect_invalid_date_format_passed_through(self, mock_fetch):
        mock_fetch.return_value = Path("/tmp/fake_invalid_date.pdf")
        self.assertEqual(self.run_main_for_test(["collect", "--date", "NOT-A-DATE"]), 0)
        mock_fetch.assert_called_once_with(date_str="NOT-A-DATE", dry_run=False, verbose=False)

    @patch("logging.basicConfig")
    def test_verbose_flag_sets_debug_level_basicConfig(self, mock_basic_config):
        with patch.object(pipeline, "_update_ratings_logic", MagicMock()): # Corrected
            self.run_main_for_test(["--verbose", "update"])
        called_with_debug = any(call_args.kwargs.get("level") == logging.DEBUG for call_args in mock_basic_config.call_args_list)
        self.assertTrue(called_with_debug, "logging.basicConfig was not called with logging.DEBUG when --verbose was used.")

    @patch("logging.getLogger")
    def test_verbose_logging_capture_for_update(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        with patch.object(pipeline, "_update_ratings_logic", MagicMock()): # Corrected
            self.run_main_for_test(["--verbose", "update"])
        self.assertTrue(mock_logger_instance.debug.called)
        self.assertTrue(any("Update command called with args" in str(arg_call) for arg_call in mock_logger_instance.debug.call_args_list))

    @patch("logging.getLogger")
    def test_dry_run_logging_capture_for_collect(self, mock_get_logger):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        self.run_main_for_test(["collect", "--date", "2024-01-01", "--dry-run"])
        dry_run_fetch_logged = any("DRY-RUN: Would fetch TJRO PDF for date: 2024-01-01" in str(call_arg) for call_arg in mock_logger_instance.info.call_args_list)
        self.assertTrue(dry_run_fetch_logged, f"Expected DRY-RUN info log not found. Actual: {mock_logger_instance.info.call_args_list}")

class TestPipelineUpdateCommand(unittest.TestCase):
    def setUp(self):
        if pipeline is None: self.fail("The 'pipeline' module could not be imported.")
        self.base_data_path = PROJECT_ROOT / "causaganha" / "data"
        self.json_input_dir = self.base_data_path / "json"; self.json_input_dir.mkdir(parents=True, exist_ok=True)
        self.processed_json_dir = self.base_data_path / "json_processed"; self.processed_json_dir.mkdir(parents=True, exist_ok=True)
        self.ratings_csv_path = self.base_data_path / "ratings.csv"
        self.partidas_csv_path = self.base_data_path / "partidas.csv"
        self.sample_decision_1 = {"numero_processo": "001", "tipo_decisao": "sentença", "polo_ativo": ["PA"], "polo_passivo": ["PB"], "advogados_polo_ativo": ["AdvA"], "advogados_polo_passivo": ["AdvB"], "resultado": "procedente", "data_decisao": "2023-01-01"}
        self.sample_decision_2 = {"numero_processo": "002", "tipo_decisao": "sentença", "polo_ativo": ["PC"], "polo_passivo": ["PD"], "advogados_polo_ativo": ["AdvC"], "advogados_polo_passivo": ["AdvA"], "resultado": "improcedente", "data_decisao": "2023-01-02"}
        self.sample_decision_3 = {"numero_processo": "003", "tipo_decisao": "acordao", "polo_ativo": ["PE"], "polo_passivo": ["PF"], "advogados_polo_ativo": ["AdvA", "AdvD"], "advogados_polo_passivo": ["AdvB"], "resultado": "provido", "data_decisao": "2023-01-03"}
        with open(self.json_input_dir / "decision1.json", "w") as f: json.dump({"decisions": [self.sample_decision_1]}, f)
        with open(self.json_input_dir / "decision2.json", "w") as f: json.dump([self.sample_decision_2], f)
        with open(self.json_input_dir / "decision3.json", "w") as f: json.dump({"decisions": [self.sample_decision_3]}, f)
        initial_ratings_df = pd.DataFrame({"advogado_id": pd.Series([], dtype='object'), "mu": pd.Series([], dtype='float'), "sigma": pd.Series([], dtype='float'), "total_partidas": pd.Series([], dtype='int')}).set_index("advogado_id")
        initial_ratings_df.to_csv(self.ratings_csv_path)
        if self.partidas_csv_path.exists(): self.partidas_csv_path.unlink()
        self.stdout_patch = patch("sys.stdout", new_callable=StringIO); self.mock_stdout = self.stdout_patch.start()
        self.stderr_patch = patch("sys.stderr", new_callable=StringIO); self.mock_stderr = self.stderr_patch.start()
        logging.getLogger().addHandler(logging.NullHandler())

    def tearDown(self):
        for f_name in ["decision1.json", "decision2.json", "decision3.json"]:
            if (self.json_input_dir / f_name).exists(): (self.json_input_dir / f_name).unlink()
            if (self.processed_json_dir / f_name).exists(): (self.processed_json_dir / f_name).unlink()
        if self.ratings_csv_path.exists(): self.ratings_csv_path.unlink()
        if self.partidas_csv_path.exists(): self.partidas_csv_path.unlink()
        self.stdout_patch.stop(); self.stderr_patch.stop()
        logging.getLogger().handlers.clear()

    @patch("pipeline.shutil.move")
    @patch("pipeline.pd.DataFrame.to_csv")
    @patch("pipeline.pd.read_csv")
    def test_update_command_valid_decisions(self, mock_read_csv, mock_to_csv, mock_shutil_move):
        initial_ratings_df = pd.DataFrame({"advogado_id": pd.Series([], dtype='object'),"mu": pd.Series([], dtype='float'),"sigma": pd.Series([], dtype='float'),"total_partidas": pd.Series([], dtype='int')}).set_index("advogado_id")
        mock_read_csv.return_value = initial_ratings_df.copy()
        args = pipeline.argparse.Namespace(dry_run=False, verbose=True)
        pipeline.update_command(args)
        mock_read_csv.assert_called_once_with(Path("causaganha/data/ratings.csv"), index_col="advogado_id")
        self.assertEqual(mock_to_csv.call_count, 2)
        self.assertEqual(mock_shutil_move.call_count, 3)
        relative_input_path = Path("causaganha/data/json"); relative_processed_path = Path("causaganha/data/json_processed")
        mock_shutil_move.assert_any_call(str(relative_input_path / "decision1.json"), str(relative_processed_path / "decision1.json"))
        mock_shutil_move.assert_any_call(str(relative_input_path / "decision2.json"), str(relative_processed_path / "decision2.json"))
        mock_shutil_move.assert_any_call(str(relative_input_path / "decision3.json"), str(relative_processed_path / "decision3.json"))
        self.assertEqual(mock_to_csv.call_args_list[0].args[0], Path("causaganha/data/ratings.csv"))
        self.assertEqual(mock_to_csv.call_args_list[1].args[0], Path("causaganha/data/partidas.csv"))
        self.assertEqual(mock_to_csv.call_args_list[1].kwargs.get("index"), False)

    @patch("pipeline.shutil.move")
    @patch("pipeline.pd.DataFrame.to_csv")
    @patch("pipeline.pd.read_csv")
    def test_update_command_dry_run(self, mock_read_csv, mock_to_csv, mock_shutil_move):
        initial_ratings_df = pd.DataFrame({"advogado_id": [], "mu": [], "sigma": [], "total_partidas": []}).set_index("advogado_id")
        mock_read_csv.return_value = initial_ratings_df.copy()
        args = pipeline.argparse.Namespace(dry_run=True, verbose=True)
        pipeline.update_command(args)
        mock_read_csv.assert_called_once_with(Path("causaganha/data/ratings.csv"), index_col="advogado_id")
        mock_to_csv.assert_not_called()
        mock_shutil_move.assert_not_called()

    @patch("pipeline.validate_decision", return_value=False)
    @patch("pipeline.shutil.move")
    @patch("pipeline.pd.DataFrame.to_csv")
    @patch("pipeline.pd.read_csv")
    def test_update_command_all_decisions_invalid(self, mock_read_csv, mock_to_csv, mock_shutil_move, mock_validate):
        initial_ratings_df = pd.DataFrame({"advogado_id": pd.Series([], dtype='object'), "mu": pd.Series([], dtype='float'), "sigma": pd.Series([], dtype='float'), "total_partidas": pd.Series([], dtype='int')}).set_index("advogado_id")
        mock_read_csv.return_value = initial_ratings_df.copy()
        args = pipeline.argparse.Namespace(dry_run=False, verbose=True)
        pipeline.update_command(args)
        self.assertEqual(mock_to_csv.call_count, 1)
        self.assertEqual(mock_to_csv.call_args_list[0].args[0], Path("causaganha/data/ratings.csv"))
        mock_shutil_move.assert_not_called()
        self.assertTrue(mock_validate.call_count >= 3)

if __name__ == "__main__":
    logging.disable(logging.NOTSET)
    logging.basicConfig(level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s")
    unittest.main(argv=sys.argv[:1], verbosity=2, exit=False)
```
