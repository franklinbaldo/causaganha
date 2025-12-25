import json
import os
from unittest.mock import patch

from causaganha.config import Settings


def test_settings_courts_default() -> None:
    """Test that COURTS defaults to ['TJRO']."""
    # Use a clean environment without COURTS set
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.COURTS == ["TJRO"]


def test_settings_courts_env_var_json() -> None:
    """Test that COURTS can be set via environment variable as JSON."""
    courts = ["TJMT", "TJAC"]
    with patch.dict(os.environ, {"COURTS": json.dumps(courts)}):
        settings = Settings()
        assert settings.COURTS == courts
