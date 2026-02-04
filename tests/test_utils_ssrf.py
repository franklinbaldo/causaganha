import pytest

from causaganha.utils import validate_url


def test_validate_url_valid():
    assert validate_url("https://example.com") == "https://example.com"
    assert validate_url("http://google.com/search?q=1") == "http://google.com/search?q=1"


def test_validate_url_invalid_scheme():
    with pytest.raises(ValueError, match="Invalid URL scheme: ftp"):
        validate_url("ftp://example.com")
    with pytest.raises(ValueError, match="Invalid URL scheme"):
        validate_url("file:///etc/passwd")


def test_validate_url_blocked_host():
    with pytest.raises(ValueError, match="Blocked: localhost access"):
        validate_url("http://localhost:8000")
    with pytest.raises(ValueError, match="Blocked: localhost access"):
        validate_url("http://127.0.0.1/api")
    with pytest.raises(ValueError, match="Blocked: localhost access"):
        validate_url("http://0.0.0.0")


def test_validate_url_valid_ip():
    assert validate_url("http://8.8.8.8") == "http://8.8.8.8"
