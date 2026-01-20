import pytest
from unittest.mock import MagicMock, patch
from repo.features.governance import GovernanceManager

@pytest.fixture
def gov():
    return GovernanceManager(root_dir=".")

def test_is_persona_pleaded_no_history(gov):
    with patch("subprocess.run") as mock_run:
        # Mock git log returning empty (no history)
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        assert gov.is_persona_pleaded("artisan") is False

def test_is_persona_pleaded_valid_plead(gov):
    with patch("subprocess.run") as mock_run:
        # Mock persona has a plead commit
        mock_run.return_value = MagicMock(stdout="hash2 [PLEAD] artisan\nhash1 initial\n", returncode=0)
        assert gov.is_persona_pleaded("artisan") is True

def test_is_persona_pleaded_historical_plead_still_valid(gov):
    """With append-only constitution, any historical plead is valid."""
    with patch("subprocess.run") as mock_run:
        # Mock: persona has an old plead, constitution has new amendments
        mock_run.return_value = MagicMock(
            stdout="hash3 new amendment\nhash2 [PLEAD] artisan\nhash1 initial\n", 
            returncode=0
        )
        # Historical plead is STILL VALID in append-only model
        assert gov.is_persona_pleaded("artisan") is True
