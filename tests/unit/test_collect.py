import os
import sys
from unittest.mock import MagicMock, patch


# Add repository root to path so we can import scripts
sys.path.append(os.getcwd())

from scripts.pipeline.collect import calculate_exit_code, collect_data


@patch("scripts.pipeline.collect.mark_downloaded")
@patch("scripts.pipeline.collect.get_db_connection")
@patch("scripts.pipeline.collect._process_item")
@patch("scripts.pipeline.collect.fetch_backfill_items")
@patch("scripts.pipeline.collect.get_existing_files_for_dates")
@patch("scripts.pipeline.collect._get_ia_s3_auth")
@patch("scripts.pipeline.collect.fetch_tribunais_from_api")
@patch("scripts.pipeline.collect.init_db")
def test_collect_data_marks_downloaded(
    mock_init_db,
    mock_tribunais,
    mock_get_ia_auth,
    mock_existing,
    mock_backfill,
    mock_process,
    mock_get_db,
    mock_mark,
):
    # Setup mocks
    mock_get_ia_auth.return_value = "LOW key:secret"
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
    mock_mark.assert_called_with(mock_con, [("2024-01-01", "TJSP")])


def test_calculate_exit_code_success():
    stats = {"success": 100, "failed": 0, "skipped": 0, "downloaded_mb": 1.0}
    assert calculate_exit_code(stats) == 0


def test_calculate_exit_code_partial_success_above_threshold():
    # 290 success, 4710 failed -> 5.8% > 5%
    stats = {"success": 290, "failed": 4710, "skipped": 0, "downloaded_mb": 270.2}
    assert calculate_exit_code(stats) == 0


def test_calculate_exit_code_below_threshold():
    # 4 success, 96 failed -> 4% < 5%
    stats = {"success": 4, "failed": 96, "skipped": 0, "downloaded_mb": 1.0}
    assert calculate_exit_code(stats) == 1


def test_calculate_exit_code_at_threshold():
    # 5 success, 95 failed -> 5% == 5%
    stats = {"success": 5, "failed": 95, "skipped": 0, "downloaded_mb": 1.0}
    assert calculate_exit_code(stats) == 0


def test_calculate_exit_code_failure():
    # 0 success, 100 failed -> 0% < 5%
    stats = {"success": 0, "failed": 100, "skipped": 0, "downloaded_mb": 0.0}
    assert calculate_exit_code(stats) == 1


def test_calculate_exit_code_empty():
    # Nothing to process -> should pass
    stats = {"success": 0, "failed": 0, "skipped": 0, "downloaded_mb": 0.0}
    assert calculate_exit_code(stats) == 0
