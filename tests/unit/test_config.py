import os
from unittest.mock import patch

from causaganha.config import Settings


def test_default_courts():
    """Test that default courts are set correctly."""
    # Ensure no env var interferes
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.COURTS == ["TJRO"]

def test_multiple_courts_from_env_json():
    """Test loading multiple courts from JSON string in env var."""
    with patch.dict(os.environ, {"COURTS": '["TJRO", "TJMT"]', "IA_ACCESS_KEY": "test", "IA_SECRET_KEY": "test"}, clear=True):
        settings = Settings()
        assert settings.COURTS == ["TJRO", "TJMT"]

def test_multiple_courts_override():
    """Test overriding courts programmatically."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings(COURTS=["TJSP", "TJRS"])
        assert settings.COURTS == ["TJSP", "TJRS"]
