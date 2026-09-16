"""Ad-hoc HTML-to-plain-text cleaner for djen_sample candidates whose
texto_limpo retains raw, sometimes malformed, HTML markup (unclosed <br>,
<html><head><meta>...>body> wrapper). Not a production script -- scratch
tool for this round's candidate selection.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser


_BLOCK_TAGS = {"p", "tr", "section", "div", "header", "article", "table", "body", "html"}
_BREAK_TAGS = {"br"}
# "meta" is deliberately excluded: the source HTML never closes it
# (no </meta>), so tracking it as a depth-incrementing drop tag would
# never decrement back to zero and would silently swallow every tag that
# follows (discovered live: it emptied TJMG/TJRS/TJTO's cleaned output).
# It has no text content worth dropping anyway.
_DROP_CONTENT_TAGS = {"style", "script", "head"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._drop_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in _DROP_CONTENT_TAGS:
            self._drop_depth += 1
        elif tag in _BREAK_TAGS or tag in _BLOCK_TAGS:
            self.parts.append("\n")
        elif tag == "td":
            self.parts.append(" ")

    def handle_startendtag(self, tag, attrs):
        if tag in _BREAK_TAGS or tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _DROP_CONTENT_TAGS:
            self._drop_depth = max(0, self._drop_depth - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._drop_depth == 0:
            self.parts.append(data)


def clean_html(raw: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(raw)
    text = "".join(extractor.parts)
    # Collapse runs of blank/whitespace-only lines, but keep single newlines
    # and internal spacing exactly as extracted otherwise -- no aggressive
    # whitespace collapsing (a prior round found silent whitespace collapse
    # itself causes verbatim-fidelity annotation defects).
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
