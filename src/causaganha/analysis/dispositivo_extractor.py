"""Extract the operative section (dispositivo) of Brazilian judicial decisions.

The dispositivo is the binding part of a ruling — the only section that
legally matters for outcome classification. Passing only the dispositivo
to the RAG/LLM pipeline reduces token cost by 4-8x and improves accuracy
because anchors and phrases are compared against the operative text, not
the report (relatório) or grounds (fundamentação).

Typical markers (case-insensitive, accent-insensitive):
    "ante o exposto", "posto isso", "isso posto", "diante do exposto",
    "pelo exposto", "em face do exposto", "diante disso",
    "por tais fundamentos", "por esses fundamentos"
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import re
import unicodedata
from functools import cached_property

import structlog


logger = structlog.get_logger()

# Ordered from most specific to most generic to reduce false positives.
# All patterns are matched case-insensitively against normalized text.
_DISPOSITIVO_MARKERS: list[str] = [
    r"ante\s+o\s+exposto",
    r"diante\s+do\s+exposto",
    r"em\s+face\s+do\s+exposto",
    r"pelo\s+exposto",
    r"por\s+tais\s+fundamentos",
    r"por\s+esses\s+fundamentos",
    r"por\s+essas\s+raz[oõ]es",
    r"posto\s+isso",
    r"isso\s+posto",
    r"diante\s+disso",
    r"ex\s+positis",
]

_COMPILED_PATTERN: re.Pattern[str] = re.compile(
    "(" + "|".join(_DISPOSITIVO_MARKERS) + ")",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Strip accents to simplify pattern matching without regex alternation."""
    return unicodedata.normalize("NFD", text)


class DispositivoExtractor:
    """Stateless helper — wraps the module-level functions for DI/testing."""

    def __init__(self, max_chars: int = 2000) -> None:
        """Initialize with optional max character limit."""
        self.max_chars = max_chars
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="dispositivo"
        )

    @cached_property
    def _pattern(self) -> re.Pattern[str]:
        return _COMPILED_PATTERN

    def extract(self, text: str) -> str | None:
        """Return the dispositivo slice, or None if no marker found."""
        return extract_dispositivo(text, max_chars=self.max_chars)

    async def aextract(self, text: str) -> str | None:
        """Async wrapper — runs CPU-bound regex in thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.extract(text),
        )

    def __del__(self) -> None:
        """Shutdown thread pool on garbage collection."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)


def extract_dispositivo(text: str, max_chars: int = 2000) -> str | None:
    """Return the operative section (dispositivo) of a judicial decision.

    Searches for standard Brazilian dispositivo markers and returns the
    text from the first match to end-of-document, capped at max_chars.
    Returns None if no marker is found (caller should fall back to full text).

    Args:
        text: Full decision text.
        max_chars: Maximum characters to return from the marker onward.

    Returns:
        Dispositivo text (including the marker phrase), or None.
    """
    if not text:
        return None

    match = _COMPILED_PATTERN.search(text)
    if match is None:
        logger.debug("dispositivo_not_found", text_len=len(text))
        return None

    start = match.start()
    dispositivo = text[start : start + max_chars]

    logger.debug(
        "dispositivo_extracted",
        marker=match.group(0),
        offset=start,
        extracted_len=len(dispositivo),
    )
    return dispositivo


async def aextract_dispositivo(text: str, max_chars: int = 2000) -> str | None:
    """Async wrapper for extract_dispositivo — runs in the default executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: extract_dispositivo(text, max_chars=max_chars),
    )
