import unittest
import subprocess # To run the pipeline script as a command-line tool
import json # To parse JSON output if testing logging (optional for this step)
import pathlib
import sys

# Add causaganha to sys.path to allow direct import of legalelo
# This is often needed when running tests from the tests directory or via discovery
# sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
# from causaganha.legalelo import pipeline # If directly testing functions

# For CLI testing, we'll primarily use subprocess to call the script.
# However, for more direct argparse testing, we might want to import the parser setup.
# Let's try to import the main_parser setup from pipeline.py
# This requires pipeline.py to be structured to allow this (e.g., parser setup in a function)
# For now, focusing on testing CLI through subprocess.
# If pipeline.py's main() is refactored to return the parser, we can test it directly.

# Alternative: Test the `create_parser()` part of pipeline.py if we refactor it.
# For now, we'll test the command line interface by calling the script.
# This means we are testing the *effects* of argparse, not the parser object directly.

class TestPipelineCLI(unittest.TestCase):

    REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
    PIPELINE_MODULE_PATH = "causaganha.legalelo.pipeline" # For python -m

    def run_pipeline_command(self, args_list):
        """Helper to run the pipeline script via python -m and return output."""
        command = [sys.executable, "-m", self.PIPELINE_MODULE_PATH] + args_list
        # print(f"Running command: {' '.join(command)}") # For debugging tests; avoid if logger is not set for test runner
        process = subprocess.run(command, capture_output=True, text=True, cwd=self.REPO_ROOT)
        return process

    def test_global_help(self):
        process = self.run_pipeline_command(["--help"])
        # Help goes to STDOUT
        self.assertEqual(process.returncode, 0, f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}")
        self.assertIn("CausaGanha Pipeline", process.stdout)
        self.assertIn("collect", process.stdout)
        self.assertIn("extract", process.stdout)
        self.assertIn("update", process.stdout)
        self.assertIn("run", process.stdout)

    def test_global_verbose_dry_run_flags(self):
        process = self.run_pipeline_command(["--verbose", "--dry-run", "update"])
        self.assertEqual(process.returncode, 0, f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}")

        # JSON logs go to STDERR by default with StreamHandler
        self.assertIn('"message": "Verbose mode enabled."', process.stderr) # Added period
        self.assertIn('"dry_run_global": true', process.stderr)
        self.assertIn('"message": "Dry-run: Would iterate JSONs, process matches, update Elo ratings."', process.stderr)

    def test_collect_command_valid_date(self):
        process = self.run_pipeline_command(["--dry-run", "collect", "--date", "2023-01-01"])
        self.assertEqual(process.returncode, 0, f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}")
        # Check STDERR for JSON logs
        self.assertIn('"command": "collect"', process.stderr)
        self.assertIn('"date": "2023-01-01"', process.stderr)

    def test_collect_command_missing_date(self):
        process = self.run_pipeline_command(["collect"])
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("arguments are required: --date", process.stderr)

    def test_extract_command_valid_pdf(self):
        dummy_pdf_dir = self.REPO_ROOT / "causaganha" / "data" / "diarios"
        dummy_pdf_dir.mkdir(parents=True, exist_ok=True)
        dummy_pdf_path = dummy_pdf_dir / "test_extract_cli.pdf"
        with open(dummy_pdf_path, "w") as f:
            f.write("dummy pdf content")

        process = self.run_pipeline_command([
            "--dry-run", "extract", "--pdf_file", str(dummy_pdf_path)
        ])
        self.assertEqual(process.returncode, 0, f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}")
        self.assertIn('"command": "extract"', process.stderr) # STDERR for logs
        # The path in JSON log might be escaped or slightly different depending on OS/json logger.
        # A more robust check would parse the JSON if this becomes flaky.
        self.assertIn(f'"pdf_file": "{str(dummy_pdf_path)}"', process.stderr.replace("\\\\", "\\"))

        custom_json_dir = self.REPO_ROOT / "causaganha" / "data" / "test_json_output_cli"
        # Ensure custom_json_dir does not persist or is cleaned if created by script
        process = self.run_pipeline_command([
            "--dry-run", "extract", "--pdf_file", str(dummy_pdf_path),
            "--json_output_dir", str(custom_json_dir)
        ])
        self.assertEqual(process.returncode, 0, f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}")
        # The log uses "output_dir" as the key in the 'extra' dict for this specific message
        self.assertIn(f'"output_dir": "{str(custom_json_dir)}"', process.stderr.replace("\\\\", "\\"))

        dummy_pdf_path.unlink()

    def test_extract_command_missing_pdf(self):
        process = self.run_pipeline_command(["extract"])
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("arguments are required: --pdf_file", process.stderr)

    def test_update_command_defaults(self):
        process = self.run_pipeline_command(["--dry-run", "update"])
        self.assertEqual(process.returncode, 0, f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}")
        self.assertIn('"command": "update"', process.stderr) # STDERR for logs
        # Check for default paths in logs - use parts of paths to be more robust
        self.assertIn(str(pathlib.Path("causaganha/data/json")), process.stderr.replace("\\\\", "\\"))
        self.assertIn(str(pathlib.Path("causaganha/data/ratings.csv")), process.stderr.replace("\\\\", "\\"))
        self.assertIn(str(pathlib.Path("causaganha/data/partidas.csv")), process.stderr.replace("\\\\", "\\"))

    def test_update_command_custom_paths(self):
        process = self.run_pipeline_command([
            "--dry-run", "update",
            "--json_dir", "custom_json",
            "--ratings_file", "custom_ratings.csv",
            "--matches_file", "custom_matches.csv"
        ])
        self.assertEqual(process.returncode, 0, f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}")
        self.assertIn('"json_dir": "custom_json"', process.stderr.replace("\\\\", "\\"))
        self.assertIn('"ratings_file": "custom_ratings.csv"', process.stderr.replace("\\\\", "\\")) # STDERR for logs
        self.assertIn('"matches_file": "custom_matches.csv"', process.stderr.replace("\\\\", "\\")) # STDERR for logs

    def test_run_command_valid_date(self):
        process = self.run_pipeline_command(["--dry-run", "run", "--date", "2023-02-01"])
        self.assertEqual(process.returncode, 0, f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}")
        self.assertIn("Handling full pipeline run", process.stderr) # Corrected message
        self.assertIn('"date": "2023-02-01"', process.stderr) # STDERR for logs
        self.assertIn("Stage 1: Collect", process.stderr) # STDERR for logs
        self.assertIn("Stage 2: Extract", process.stderr) # STDERR for logs
        self.assertIn("Stage 3: Update", process.stderr) # STDERR for logs

    def test_run_command_missing_date(self):
        process = self.run_pipeline_command(["run"])
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("arguments are required: --date", process.stderr)

if __name__ == '__main__':
    unittest.main()
