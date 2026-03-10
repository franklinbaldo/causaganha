import unittest
from datetime import date
from unittest.mock import patch

from scripts.pipeline.consolidate import ConsolidationContext, find_next_unconsolidated


class TestConsolidateBackfill(unittest.TestCase):
    def setUp(self):
        # Each test gets a fresh context (no shared mutable globals)
        self.ctx = ConsolidationContext()

        # Ensure CheckpointManager is mocked for all tests to avoid side effects
        # and ensure load() returns None (no checkpoint) by default.
        self.checkpoint_patcher = patch("scripts.pipeline.consolidate.CheckpointManager")
        self.mock_checkpoint_cls = self.checkpoint_patcher.start()
        # By default, load() returns a Mock, which is truthy. We need it to be None.
        self.mock_checkpoint_cls.return_value.load.return_value = None

    def tearDown(self):
        self.checkpoint_patcher.stop()

    @patch("scripts.pipeline.consolidate.fetch_consolidation_candidates")
    def test_find_next_unconsolidated_uses_manifest_candidates(self, mock_fetch_candidates):
        # Setup: Manifest returns candidates
        mock_fetch_candidates.return_value = ["2026-01-01", "2026-01-02"]

        # First call should return first candidate
        result1 = find_next_unconsolidated(ctx=self.ctx)
        assert result1 == "2026-01-01"

        # Second call should return second candidate (popped from cached list)
        result2 = find_next_unconsolidated(ctx=self.ctx)
        assert result2 == "2026-01-02"

        # Third call should trigger fallback (mock fetch called only once)
        # We need to mock the fallback path now to return None or something
        with patch("scripts.pipeline.consolidate._needs_consolidation", return_value=False):
            with patch("scripts.pipeline.consolidate._all_tribunals_stopped", return_value=True):
                result3 = find_next_unconsolidated(ctx=self.ctx)
                assert result3 is None

        mock_fetch_candidates.assert_called_once()

    @patch("scripts.pipeline.consolidate.fetch_consolidation_candidates")
    @patch("scripts.pipeline.consolidate._all_tribunals_stopped")
    @patch("scripts.pipeline.consolidate._needs_consolidation")
    def test_find_next_unconsolidated_newest_first(
        self, mock_needs_consolidation, mock_all_stopped, mock_fetch_candidates
    ):
        # Force fallback to walking logic by returning empty list
        mock_fetch_candidates.return_value = []

        # Mock date.today() but keep date constructor working
        # We patch 'scripts.pipeline.consolidate.date' with a wrapper that delegates
        # everything to the real datetime.date except .today()
        class MockDate(date):
            @classmethod
            def today(cls):
                return date(2026, 1, 1)

        with patch("scripts.pipeline.consolidate.date", MockDate):
            mock_all_stopped.return_value = False  # Tribunals still active

            # Scenario:
            # 2024-01-01 needs consolidation (oldest)
            # 2025-01-01 needs consolidation
            # 2026-01-01 needs consolidation (newest - today)

            def needs_consolidation_side_effect(
                d_str, manifest=None, must_be_complete=False, **kwargs
            ):
                return d_str in ["2024-01-01", "2025-01-01", "2026-01-01"]

            mock_needs_consolidation.side_effect = needs_consolidation_side_effect

            # With newest-first logic, we expect 2026-01-01 (most recent) to be returned.
            result = find_next_unconsolidated()

            assert result == "2026-01-01", f"Expected 2026-01-01 but got {result}"

    @patch("scripts.pipeline.consolidate.fetch_consolidation_candidates")
    @patch("scripts.pipeline.consolidate._all_tribunals_stopped")
    @patch("scripts.pipeline.consolidate._needs_consolidation")
    def test_find_next_unconsolidated_skips_weekends(
        self, mock_needs_consolidation, mock_all_stopped, mock_fetch_candidates
    ):
        # Force fallback
        mock_fetch_candidates.return_value = []

        # Mock date.today() but keep date constructor working
        class MockDate(date):
            @classmethod
            def today(cls):
                return date(2024, 1, 10)  # Wednesday

        with patch("scripts.pipeline.consolidate.date", MockDate):
            mock_all_stopped.return_value = False  # Tribunals still active

            # Scenario:
            # 2024-01-10 (Wed, today) -> Consolidated (False)
            # 2024-01-09 (Tue) -> Unconsolidated (True) -> Expect Return
            # 2024-01-08 (Mon) -> Unconsolidated (True)
            # 2024-01-07 (Sun) -> Weekend (Skip)
            # 2024-01-06 (Sat) -> Weekend (Skip)
            # 2024-01-05 (Fri) -> Consolidated (False)

            def side_effect(d_str, manifest=None, must_be_complete=False, **kwargs):
                if d_str in {"2024-01-10", "2024-01-05"}:
                    return False  # Already done
                return True  # Others need consolidation

            mock_needs_consolidation.side_effect = side_effect

            # With Newest First logic (d-0, d-1, d-2, ...):
            # 1. 2024-01-10 (Wed, today) -> check -> False
            # 2. 2024-01-09 (Tue) -> check -> True -> Return

            result = find_next_unconsolidated()

            assert result == "2024-01-09"

    @patch("scripts.pipeline.consolidate.fetch_consolidation_candidates")
    @patch("scripts.pipeline.consolidate._all_tribunals_stopped")
    @patch("scripts.pipeline.consolidate._needs_consolidation")
    def test_find_next_unconsolidated_stops_when_all_tribunals_stopped(
        self, mock_needs_consolidation, mock_all_stopped, mock_fetch_candidates
    ):
        # Force fallback
        mock_fetch_candidates.return_value = []

        # Mock date.today() but keep date constructor working
        class MockDate(date):
            @classmethod
            def today(cls):
                return date(2026, 1, 1)

        with patch("scripts.pipeline.consolidate.date", MockDate):
            # All dates are consolidated already
            mock_needs_consolidation.return_value = False

            # Simulate: after going back 10 days, all tribunals are stopped
            call_count = [0]

            def all_stopped_side_effect(d, manifest=None, **kwargs):
                call_count[0] += 1
                # First 10 calls: not all stopped
                # 11th call onwards: all stopped
                return call_count[0] > 10

            mock_all_stopped.side_effect = all_stopped_side_effect

            result = find_next_unconsolidated()

            # Should return None (backfill complete)
            assert result is None
            # Should have stopped checking after all tribunals stopped
            assert call_count[0] > 10
