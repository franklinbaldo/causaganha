"""Shared smart-truncation helper for embedders.

Both ``LocalEmbedder`` and ``ApiEmbedder`` cap input length with the same
head+tail strategy, so the logic lives here to avoid divergence.
"""

from __future__ import annotations


# Smart truncation guard. pplx-embed / Jina v3 have a 32K token context,
# which is ~100K chars of Portuguese legal text. Virtually no judicial
# intimação exceeds this, so the guard is a safety net rather than the norm.
SMART_TRUNCATE_CHARS = 100_000


def smart_truncate(text: str, max_chars: int = SMART_TRUNCATE_CHARS) -> str:
    """Keep the head + tail of ``text`` when it exceeds ``max_chars``.

    Drops the middle, joining the two halves with a newline ``[...]`` marker.
    This preserves the document head (parties, case number) and tail
    (dispositivo) — the parts that matter most for judicial outcome
    analysis — while staying under the embedding model's context window.
    """
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n[...]\n" + text[-half:]
