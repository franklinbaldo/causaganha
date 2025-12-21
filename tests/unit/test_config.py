import os
from unittest import mock
import pytest
from pathlib import Path

def test_settings_defaults():
    from causaganha.config import Settings
    settings = Settings()
    assert settings.GCP_PROJECT == "my-project"
    assert "TJRO" in settings.COURTS
    assert isinstance(settings.DATA_DIR, Path)

def test_settings_env_override_json():
    with mock.patch.dict(os.environ, {
        "GCP_PROJECT": "prod-project",
        "COURTS": '["TJSP", "TJRO"]',
        "LOOKBACK_DAYS": "7"
    }):
        from causaganha.config import Settings
        settings = Settings()
        assert settings.GCP_PROJECT == "prod-project"
        assert "TJSP" in settings.COURTS
        assert "TJRO" in settings.COURTS
        assert len(settings.COURTS) == 2
