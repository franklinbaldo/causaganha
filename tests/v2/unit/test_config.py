import os
from unittest import mock

from causaganha.config import Settings


def test_settings_courts_parsing() -> None:
    """Test that COURTS list is parsed correctly from JSON string in env var."""
    with mock.patch.dict(os.environ, {"COURTS": '["TJSP", "TJMG"]'}):
        settings = Settings()
        assert settings.COURTS == ["TJSP", "TJMG"]


def test_settings_courts_default() -> None:
    """Test that COURTS has a default value."""
    # Ensure COURTS is not in env
    old_environ = dict(os.environ)
    if "COURTS" in os.environ:
        del os.environ["COURTS"]

    try:
        settings = Settings(_env_file=None)
        assert settings.COURTS == ["TJRO"]
    finally:
        os.environ.clear()
        os.environ.update(old_environ)
