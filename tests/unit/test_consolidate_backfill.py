import unittest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
from scripts.pipeline.consolidate import find_next_unconsolidated


class TestConsolidateBackfill(unittest.TestCase):
    @patch("scripts.pipeline.consolidate.date")
    @patch("scripts.pipeline.consolidate._needs_consolidation")
    def test_find_next_unconsolidated_newest_first(self, mock_needs_consolidation, mock_date):
        # Setup: Today is 2026-01-01 (Wednesday)
        today = date(2026, 1, 1)  # Wednesday
        mock_date.today.return_value = today

        # Scenario:
        # 2024-01-01 needs consolidation (oldest)
        # 2025-01-01 needs consolidation
        # 2026-01-01 needs consolidation (newest - today)

        def needs_consolidation_side_effect(d_str, must_be_complete=False):
            if d_str in ["2024-01-01", "2025-01-01", "2026-01-01"]:
                return True
            return False

        mock_needs_consolidation.side_effect = needs_consolidation_side_effect

        # We search with max_depth covering back to 2024 (approx 730 days)
        # With newest-first logic, we expect 2026-01-01 (most recent) to be returned.

        result = find_next_unconsolidated(max_depth=800)

        self.assertEqual(result, "2026-01-01", f"Expected 2026-01-01 but got {result}")

    @patch("scripts.pipeline.consolidate.date")
    @patch("scripts.pipeline.consolidate._needs_consolidation")
    def test_find_next_unconsolidated_skips_weekends(
        self, mock_needs_consolidation, mock_date
    ):
        # Setup: Today is Wednesday 2024-01-10
        today = date(2024, 1, 10)  # Wednesday
        mock_date.today.return_value = today

        # Scenario:
        # 2024-01-10 (Wed, today) -> Consolidated (False)
        # 2024-01-09 (Tue) -> Unconsolidated (True) -> Expect Return
        # 2024-01-08 (Mon) -> Unconsolidated (True)
        # 2024-01-07 (Sun) -> Weekend (Skip)
        # 2024-01-06 (Sat) -> Weekend (Skip)
        # 2024-01-05 (Fri) -> Consolidated (False)

        def side_effect(d_str, must_be_complete=False):
            if d_str == "2024-01-10" or d_str == "2024-01-05":
                return False  # Already done
            return True  # Others need consolidation

        mock_needs_consolidation.side_effect = side_effect

        # With Newest First logic (d-0, d-1, d-2, ...):
        # 1. 2024-01-10 (Wed, today) -> check -> False
        # 2. 2024-01-09 (Tue) -> check -> True -> Return

        result = find_next_unconsolidated(max_depth=5)

        self.assertEqual(result, "2024-01-09")
