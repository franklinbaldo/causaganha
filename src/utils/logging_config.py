"""Central logging configuration for CausaGanha."""

from __future__ import annotations

import logging
import os
from typing import Optional

from pythonjsonlogger import jsonlogger

_LOGGER_INITIALIZED = False


def setup_logging(
    level: Optional[str] = None,
    fmt: Optional[str] = None,
) -> logging.Logger:
    """Configure root logger.

    Parameters
    ----------
    level:
        Logging level as a string (e.g. ``"INFO"``). Defaults to ``LOG_LEVEL``
        environment variable or ``"INFO"``.
    fmt:
        Log format, ``"json"`` for structured logs or ``"simple"`` for
        human-readable format. Defaults to ``LOG_FORMAT`` environment variable
        or ``"simple"``.

    Returns
    -------
    logging.Logger
        The configured root logger.
    """
    level_str = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    fmt = (fmt or os.getenv("LOG_FORMAT", "simple")).lower()

    log_level = getattr(logging, level_str, logging.INFO)

    handler = logging.StreamHandler()
    if fmt == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    global _LOGGER_INITIALIZED
    _LOGGER_INITIALIZED = True

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a logger, initializing the root logger if necessary."""
    if not _LOGGER_INITIALIZED:
        setup_logging()
    return logging.getLogger(name)
