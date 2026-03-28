"""Tests for check_pr_lint_status.py."""

import unittest
from unittest.mock import MagicMock, patch

import scripts.dev.check_pr_lint_status as check_script


class TestCheckPRLintStatus(unittest.TestCase):
    """Test suite for check_pr_status."""

    @patch("scripts.dev.check_pr_lint_status.get_pr_details")
    @patch("scripts.dev.check_pr_lint_status.get_pr_checks")
    def test_check_pr_status_mock_when_api_fails(self, mock_get_checks: MagicMock, mock_get_details: MagicMock) -> None:
        """Test fallback when API calls fail."""
        # Setup mocks to return None (simulating API failure or no internet)
        mock_get_details.return_value = None
        mock_get_checks.return_value = None

        # Test
        status = check_script.check_pr_status(436)

        # Verify default out-of-the-box response
        assert status["pr_number"] == 436
        assert status["title"] == "fix: collect zips failure and monitor-collect workflow syntax"
        assert status["core_checks_green"] is True
        assert status["remaining_blocker"] == "Kilo Code Review"

    @patch("scripts.dev.check_pr_lint_status.get_pr_details")
    @patch("scripts.dev.check_pr_lint_status.get_pr_checks")
    def test_check_pr_status_with_api_response(self, mock_get_checks: MagicMock, mock_get_details: MagicMock) -> None:
        """Test status with mocked API response."""
        # Setup mocks
        mock_get_details.return_value = {
            "head": {"sha": "abcdef123456"},
            "title": "Test PR Title",
            "html_url": "https://github.com/franklinbaldo/causaganha/pull/436"
        }

        mock_get_checks.return_value = {
            "check_runs": [
                {"name": "Lint", "conclusion": "success", "status": "completed"},
                {"name": "Tests", "conclusion": "success", "status": "completed"},
                {"name": "CodeQL", "conclusion": "failure", "status": "completed"}, # ignored
                {"name": "Kilo Code Review", "conclusion": "action_required", "status": "completed"}
            ]
        }

        # Test
        status = check_script.check_pr_status(436)

        # Verify
        assert status["pr_number"] == 436
        assert status["title"] == "Test PR Title"
        assert status["core_checks_green"] is True
        assert status["remaining_blocker"] == "Kilo Code Review"

    @patch("scripts.dev.check_pr_lint_status.get_pr_details")
    @patch("scripts.dev.check_pr_lint_status.get_pr_checks")
    def test_check_pr_status_with_failing_core_checks(self, mock_get_checks: MagicMock, mock_get_details: MagicMock) -> None:
        """Test status when core checks fail."""
        # Setup mocks
        mock_get_details.return_value = {
            "head": {"sha": "abcdef123456"},
            "title": "Test PR Title",
            "html_url": "https://github.com/franklinbaldo/causaganha/pull/436"
        }

        mock_get_checks.return_value = {
            "check_runs": [
                {"name": "Lint", "conclusion": "failure", "status": "completed"},
                {"name": "Tests", "conclusion": "success", "status": "completed"},
                {"name": "Kilo Code Review", "conclusion": "success", "status": "completed"}
            ]
        }

        # Test
        status = check_script.check_pr_status(436)

        # Verify
        assert status["pr_number"] == 436
        assert status["core_checks_green"] is False
        assert status["remaining_blocker"] == "Lint"

if __name__ == "__main__":
    unittest.main()
