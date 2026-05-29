"""Tests for smart_truncate — the shared embedder input-length guard."""

from __future__ import annotations

from causaganha.analysis.text_truncate import SMART_TRUNCATE_CHARS, smart_truncate


def test_short_text_unchanged() -> None:
    text = "Julgo procedente o pedido."
    assert smart_truncate(text) == text


def test_text_at_limit_unchanged() -> None:
    text = "x" * SMART_TRUNCATE_CHARS
    assert smart_truncate(text) == text


def test_long_text_keeps_head_and_tail_drops_middle() -> None:
    head = "A" * 60_000
    tail = "B" * 60_000
    text = head + "MIDDLE_MARKER" + tail

    result = smart_truncate(text)

    # Head and tail survive; the middle (and its marker) is dropped.
    assert result.startswith("A" * 1_000)
    assert result.endswith("B" * 1_000)
    assert "MIDDLE_MARKER" not in result
    assert "[...]" in result


def test_long_text_respects_max_chars() -> None:
    text = "z" * (SMART_TRUNCATE_CHARS * 2)
    result = smart_truncate(text)
    # Two halves plus the join marker.
    assert len(result) == SMART_TRUNCATE_CHARS + len("\n[...]\n")


def test_custom_max_chars() -> None:
    text = "ab" * 100  # 200 chars
    result = smart_truncate(text, max_chars=50)
    assert len(result) == 50 + len("\n[...]\n")
    assert result.startswith("a")
