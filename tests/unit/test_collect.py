import sys
import os
from unittest.mock import MagicMock, patch

# Add repository root to path so we can import scripts
sys.path.append(os.getcwd())

from scripts.pipeline.collect import collect_data

@patch("scripts.pipeline.collect.mark_downloaded")
@patch("scripts.pipeline.collect.get_db_connection")
@patch("scripts.pipeline.collect._process_item")
@patch("scripts.pipeline.collect.fetch_backfill_items")
@patch("scripts.pipeline.collect.get_existing_files_for_dates")
@patch("scripts.pipeline.collect._get_ia_s3_auth")
@patch("scripts.pipeline.collect.fetch_tribunais_from_api")
@patch("scripts.pipeline.collect.init_db")
def test_collect_data_marks_downloaded(mock_init_db, mock_tribunais, mock_auth, mock_existing, mock_backfill, mock_process, mock_get_db, mock_mark):
    # Setup mocks
    mock_auth.return_value = "mock_auth"
    mock_existing.return_value = set()
    mock_backfill.return_value = [("2024-01-01", "TJSP")]
    mock_process.return_value = ("success", 1.0)
    mock_tribunais.return_value = ["TJSP"]

    mock_con = MagicMock()
    mock_get_db.return_value = mock_con

    # Run
    # proxy_url is required
    collect_data(proxy_url="http://mock", workers=1)

    # Verify
    # We expect mark_downloaded to be called with the success items
    # The current code DOES NOT call it, so this assertion should fail
    mock_mark.assert_called_with(mock_con, [("2024-01-01", "TJSP")])
