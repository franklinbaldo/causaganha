"""Tests for checkpointing logic in consolidate.py."""

import json
from datetime import date, timedelta
from unittest.mock import patch

# Adjusting import to work with pytest and project structure
from scripts.pipeline.consolidate import CheckpointManager, find_next_unconsolidated


class TestCheckpointManager:
    """Unit tests for CheckpointManager class."""

    def test_checkpoint_save(self, tmp_path):
        """Verify that saving a date to the checkpoint works."""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)
        test_date = "2026-01-27"

        manager.save(test_date)

        assert checkpoint_file.exists()
        with open(checkpoint_file) as f:
            data = json.load(f)
        assert data["last_checked"] == test_date

    def test_checkpoint_load(self, tmp_path):
        """Verify that loading a date from the checkpoint works."""
        checkpoint_file = tmp_path / "checkpoint.json"
        test_date = "2026-01-27"
        with open(checkpoint_file, "w") as f:
            json.dump({"last_checked": test_date}, f)

        manager = CheckpointManager(checkpoint_file)
        loaded_date = manager.load()

        assert loaded_date == test_date

    def test_checkpoint_load_none(self, tmp_path):
        """Verify that loading from a non-existent checkpoint returns None."""
        checkpoint_file = tmp_path / "non_existent.json"
        manager = CheckpointManager(checkpoint_file)
        assert manager.load() is None


@patch("scripts.pipeline.consolidate.fetch_consolidation_candidates")
@patch("scripts.pipeline.consolidate._all_tribunals_stopped")
@patch("scripts.pipeline.consolidate._needs_consolidation")
class TestConsolidationCheckpointing:
    """Tests for integration of CheckpointManager in find_next_unconsolidated."""

    def test_resumes_from_checkpoint(self, mock_needs, mock_stopped, mock_fetch, tmp_path):
        """Verify that scanning resumes from the checkpoint if restarted."""
        # Ensure manifest discovery doesn't skip the checkpoint logic
        mock_fetch.return_value = []

        checkpoint_file = tmp_path / "checkpoint.json"
        today = date.today()
        # Save "3 days ago" as last checked.
        # find_next_unconsolidated resumes from the checkpoint date itself.
        last_checked = (today - timedelta(days=3)).strftime("%Y-%m-%d")
        with open(checkpoint_file, "w") as f:
            json.dump({"last_checked": last_checked}, f)

        mock_stopped.return_value = False

        # Stop scanning after a few dates to be fast
        def needs_side_effect(d_str, *args, **kwargs):
            # Stop when we reach 10 days ago
            d = date.fromisoformat(d_str)
            return d <= today - timedelta(days=10)

        mock_needs.side_effect = needs_side_effect

        # We must clear the global cache to avoid side effects from other tests
        with patch("scripts.pipeline.consolidate._CONSOLIDATION_CANDIDATES", None):
            find_next_unconsolidated(checkpoint_file=checkpoint_file)

        # It should check dates starting from last_checked (inclusive) going backward
        # Check that it didn't check dates NEWER than last_checked
        for call in mock_needs.call_args_list:
            called_date = call.args[0]
            assert called_date <= last_checked

    def test_saves_checkpoint_after_each_date(self, mock_needs, mock_stopped, mock_fetch, tmp_path):
        """Verify that checkpoint is saved after checking each date."""
        mock_fetch.return_value = []
        checkpoint_file = tmp_path / "checkpoint.json"

        mock_stopped.return_value = False
        # Stop after some iterations by finding something
        # Find a weekday to avoid being skipped by the weekend check
        today = date.today()
        # Walk backward from today to find a weekday that's at least 3 days ago
        days_back = 3
        while True:
            candidate = today - timedelta(days=days_back)
            if candidate.weekday() < 5:  # Monday-Friday
                break
            days_back += 1
        target_date = candidate.strftime("%Y-%m-%d")

        def needs_side_effect(d_str, *args, **kwargs):
            return d_str == target_date

        mock_needs.side_effect = needs_side_effect

        with patch("scripts.pipeline.consolidate._CONSOLIDATION_CANDIDATES", None):
            find_next_unconsolidated(checkpoint_file=checkpoint_file)

        # Check if checkpoint was saved
        assert checkpoint_file.exists()
        with open(checkpoint_file) as f:
            data = json.load(f)

        # Should contain the date it found (or the last one it checked)
        assert data["last_checked"] == target_date
