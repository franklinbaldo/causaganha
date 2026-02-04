import unittest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
from scripts.pipeline.consolidate import find_next_unconsolidated


class TestConsolidateBackfill(unittest.TestCase):
    @patch("scripts.pipeline.consolidate.date")
    @patch("scripts.pipeline.consolidate._needs_consolidation")
    def test_find_next_unconsolidated_oldest_first(self, mock_needs_consolidation, mock_date):
        # Setup: Today is 2026-01-01
        today = date(2026, 1, 1)
        mock_date.today.return_value = today

        # Scenario:
        # 2024-01-01 needs consolidation (oldest)
        # 2025-01-01 needs consolidation
        # 2026-01-01 needs consolidation (newest)

        def needs_consolidation_side_effect(d_str, must_be_complete=False):
            if d_str in ["2024-01-01", "2025-01-01", "2026-01-01"]:
                return True
            return False

        mock_needs_consolidation.side_effect = needs_consolidation_side_effect

        # We search with max_depth covering back to 2024 (approx 730 days)
        # We expect 2024-01-01 to be returned if the fix is applied.

        result = find_next_unconsolidated(max_depth=800)

        self.assertEqual(result, "2024-01-01", f"Expected 2024-01-01 but got {result}")

    @patch("scripts.pipeline.consolidate.date")
    @patch("scripts.pipeline.consolidate._needs_consolidation")
    def test_find_next_unconsolidated_skips_weekends_and_future(
        self, mock_needs_consolidation, mock_date
    ):
        # Setup: Today is Wednesday 2024-01-10
        today = date(2024, 1, 10)
        mock_date.today.return_value = today

        # Scenario:
        # We search back 5 days:
        # 2024-01-05 (Friday) -> Consolidated (False)
        # 2024-01-06 (Saturday) -> Weekend (Skip)
        # 2024-01-07 (Sunday) -> Weekend (Skip)
        # 2024-01-08 (Monday) -> Unconsolidated (True) -> Expect Return
        # 2024-01-09 (Tuesday) -> Unconsolidated (True)
        # 2024-01-10 (Wednesday) -> Unconsolidated (True)

        def side_effect(d_str, must_be_complete=False):
            if d_str == "2024-01-05":
                return False  # Done
            return True  # Others need it

        mock_needs_consolidation.side_effect = side_effect

        # We start looking from 5 days ago (2024-01-05)
        # With Oldest First logic:
        # 1. 2024-01-05 (Fri) -> check -> False
        # 2. 2024-01-06 (Sat) -> skip
        # 3. 2024-01-07 (Sun) -> skip
        # 4. 2024-01-08 (Mon) -> check -> True -> Return

        result = find_next_unconsolidated(max_depth=5)

        self.assertEqual(result, "2024-01-08")
