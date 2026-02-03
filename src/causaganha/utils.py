import urllib.parse


def validate_url(url: str) -> str:
    """Validate URL to prevent SSRF attacks."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
    if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
        raise ValueError("Blocked: localhost access")
    # Add more checks as needed
    return url
