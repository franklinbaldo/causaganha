"""Tests for consolidation checkpoint logic."""

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

# Import the module to test
# Note: CheckpointManager might not exist yet, so this import might fail until implementation
from scripts.pipeline.consolidate import CheckpointManager, find_next_unconsolidated


class TestCheckpointManager:
    """BDD-style tests for CheckpointManager."""

    def test_checkpoint_save(self, tmp_path):
        """Given: Backfill runs and processes some dates
        When: Checkpoint saved
        Then: Progress file contains correct state.
        """
        # Given
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)
        test_date = "2024-01-01"

        # When
        manager.save(test_date)

        # Then
        assert checkpoint_file.exists()
        with open(checkpoint_file) as f:
            data = json.load(f)
        assert data["last_checked"] == test_date

    def test_checkpoint_resume(self, tmp_path):
        """Given: Checkpoint exists with partial progress
        When: Backfill resumed
        Then: Starts from saved position.
        """
        # Given
        checkpoint_file = tmp_path / "checkpoint.json"
        saved_date = "2024-01-15"
        with open(checkpoint_file, "w") as f:
            json.dump({"last_checked": saved_date}, f)

        manager = CheckpointManager(checkpoint_file)

        # When
        loaded_date = manager.load()

        # Then
        assert loaded_date == saved_date

    def test_checkpoint_error_handling(self, tmp_path):
        """Given: Corrupt checkpoint file
        When: Backfill starts
        Then: Gracefully handles error, starts fresh.
        """
        # Given
        checkpoint_file = tmp_path / "checkpoint.json"
        with open(checkpoint_file, "w") as f:
            f.write("{invalid-json")

        manager = CheckpointManager(checkpoint_file)

        # When
        loaded_date = manager.load()

        # Then
        assert loaded_date is None  # Should return None on error

    def test_checkpoint_boundary_empty(self, tmp_path):
        """Given: Empty checkpoint (first run)
        When: Backfill starts
        Then: Returns None.
        """
        # Given
        checkpoint_file = tmp_path / "checkpoint.json"
        # File does not exist

        manager = CheckpointManager(checkpoint_file)

        # When
        loaded_date = manager.load()

        # Then
        assert loaded_date is None

    def test_checkpoint_boundary_future(self, tmp_path):
        """Given: Checkpoint with future date
        When: Loaded
        Then: (Behavior depends on implementation, but assuming it just loads it).
        """
        # Given
        checkpoint_file = tmp_path / "checkpoint.json"
        future_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        with open(checkpoint_file, "w") as f:
            json.dump({"last_checked": future_date}, f)

        manager = CheckpointManager(checkpoint_file)

        # When
        loaded_date = manager.load()

        # Then
        assert loaded_date == future_date


@patch("scripts.pipeline.consolidate._all_tribunals_stopped")
@patch("scripts.pipeline.consolidate._needs_consolidation")
class TestFindNextUnconsolidatedWithCheckpoint:
    """Tests for integration of CheckpointManager in find_next_unconsolidated."""

    def test_resume_from_checkpoint(self, mock_needs, mock_stopped, tmp_path):
        """Given: Checkpoint says we checked up to 10 days ago
        When: find_next_unconsolidated is called
        Then: Scanning starts from 11 days ago (or 10, depending on logic).
        """
        # Setup
        checkpoint_file = tmp_path / "checkpoint.json"
        # Let's say today is 2026-01-27. 10 days ago is 2026-01-17.
        # We save 2026-01-17 as the last checked date.
        today = date.today()
        last_checked = (today - timedelta(days=10)).strftime("%Y-%m-%d")

        with open(checkpoint_file, "w") as f:
            json.dump({"last_checked": last_checked}, f)

        mock_stopped.return_value = False
        mock_needs.return_value = False  # nothing found yet

        # Mock CheckpointManager inside the module to use our tmp file
        with patch("scripts.pipeline.consolidate.CheckpointManager") as MockManager:
            # Configure the mock to return a real manager that points to our file
            real_manager = CheckpointManager(checkpoint_file)
            MockManager.return_value = real_manager

            # Use side_effect to inspect calls to _needs_consolidation
            # We want to verify that dates AFTER (more recent than) last_checked are NOT checked.
            # And dates BEFORE (older than) last_checked ARE checked.

            # Actually, find_next_unconsolidated usually starts from Today and goes back.
            # If we have a checkpoint "last_checked", it means we have already verified everything
            # from Today down to "last_checked". So we should resume scanning from "last_checked" backwards.

            # Run
            find_next_unconsolidated()

            # Verify
            # We expect _needs_consolidation to NOT be called for dates more recent than last_checked.
            # It should be called for last_checked - 1 day (or similar).

            # Extract arguments passed to _needs_consolidation
            called_dates = [call.args[0] for call in mock_needs.call_args_list]

            # Verify no date > last_checked was checked
            for d_str in called_dates:
                assert d_str <= last_checked

    def test_save_checkpoint_on_progress(self, mock_needs, mock_stopped, tmp_path):
        """Given: No checkpoint
        When: Scanning proceeds
        Then: Checkpoint is updated.
        """
        checkpoint_file = tmp_path / "checkpoint.json"

        mock_stopped.return_value = False
        # Make it find something at 5 days ago
        target_date = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")

        def needs_side_effect(d_str, *args, **kwargs):
            return d_str == target_date

        mock_needs.side_effect = needs_side_effect

        with patch("scripts.pipeline.consolidate.CheckpointManager") as MockManager:
            # We need to mock the save method to verify it's called
            mock_instance = MagicMock()
            mock_instance.load.return_value = None  # No existing checkpoint
            MockManager.return_value = mock_instance

            find_next_unconsolidated()

            # Verify save was called at least once
            assert mock_instance.save.called

            # It should have saved the target_date (or dates leading up to it)
            # The exact behavior depends on implementation (save every step vs save on find)
            # Assuming we save the date we just finished checking/found.
            # args[0] of the last call should be likely target_date or close to it
            last_call_date = mock_instance.save.call_args[0][0]
            assert last_call_date <= date.today().strftime("%Y-%m-%d")
