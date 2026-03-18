"""Internet Archive S3-compatible credential resolution."""

from __future__ import annotations

import configparser
import os
from pathlib import Path

import structlog

log = structlog.get_logger()


def get_ia_s3_auth() -> str:
    """Return the IA S3 authorization header value: ``LOW access:secret``.

    Resolution order:
    1. ``IAS3_ACCESS_KEY`` / ``IAS3_SECRET_KEY`` environment variables
    2. ``~/.config/internetarchive/ia.ini`` ``[s3]`` section
    """
    access = os.environ.get("IAS3_ACCESS_KEY", "").strip()
    secret = os.environ.get("IAS3_SECRET_KEY", "").strip()

    if access and secret:
        log.debug("ia_credentials_from_env")
        return f"LOW {access}:{secret}"

    ini_path = Path.home() / ".config" / "internetarchive" / "ia.ini"
    if ini_path.is_file():
        cfg = configparser.ConfigParser()
        cfg.read(ini_path)
        access = cfg.get("s3", "access", fallback="").strip()
        secret = cfg.get("s3", "secret", fallback="").strip()
        if access and secret:
            log.debug("ia_credentials_from_ini", path=str(ini_path))
            return f"LOW {access}:{secret}"

    msg = (
        "Internet Archive S3 credentials not found. "
        "Set IAS3_ACCESS_KEY and IAS3_SECRET_KEY environment variables, "
        "or configure ~/.config/internetarchive/ia.ini [s3] section."
    )
    raise RuntimeError(msg)
