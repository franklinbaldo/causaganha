"""Text preprocessing utilities for judicial decision analysis."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser


_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class _TagStripper(HTMLParser):
    """Minimal HTMLParser subclass that collects text nodes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def strip_html(text: str) -> str:
    """Return plain text extracted from an HTML string.

    Handles:
    - HTML tags (<p>, <br/>, <strong>, etc.)
    - Named and numeric character references (&amp;, &eacute;, &#160;)
    - Collapses runs of whitespace/newlines to a single space

    If the input contains no HTML tags, it is returned unchanged (fast path).
    """
    # Always decode entities (&amp;, &eacute;, &#160;, etc.)
    unescaped = html.unescape(text)

    # Fast path: no tags after entity decoding
    if "<" not in unescaped:
        return unescaped

    stripper = _TagStripper()
    stripper.feed(unescaped)
    stripper.close()
    result = stripper.get_text()
    return _WHITESPACE_RE.sub(" ", result).strip()


def is_html(text: str) -> bool:
    """Return True if the text appears to contain HTML markup."""
    return bool(_TAG_RE.search(text))
