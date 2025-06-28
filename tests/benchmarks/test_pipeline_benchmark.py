import time
from pathlib import Path
from unittest.mock import patch

from src import pipeline
import sys


def test_pipeline_run_time():
    """Benchmark the pipeline run command with mocked dependencies."""
    with patch("src.pipeline.fetch_tjro_pdf") as mock_fetch, \
         patch("src.pipeline.GeminiExtractor") as MockExtractor, \
         patch("src.pipeline.update_command") as mock_update:
        mock_fetch.return_value = Path("/tmp/dummy.pdf")
        extractor_instance = MockExtractor.return_value
        extractor_instance.extract_and_save_json.return_value = Path("/tmp/dummy.json")
        mock_update.return_value = None

        start = time.perf_counter()
        sys.argv = ["pipeline.py", "run", "--date", "2024-01-01", "--dry-run"]
        pipeline.main()
        duration = time.perf_counter() - start

    # Ensure the pipeline completes quickly under mocked conditions
    assert duration < 1.0
