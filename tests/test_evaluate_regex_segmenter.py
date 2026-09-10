"""Behavior tests for scripts/evaluate_regex_segmenter.py's per-row processing.

``_process_row`` must report ``was_skipped=True`` when the regex segmenter
itself produced no result (``_segment`` returning ``None``), as distinct
from a result that merely disagrees with the gold labels. A prior version
inlined this logic in ``main()``'s loop and coalesced ``None`` to ``{}``
before checking for it, making the ``skipped`` counter permanently zero.
"""

from __future__ import annotations

import pytest

from scripts import evaluate_regex_segmenter as mod


def test_process_row_reports_not_skipped_when_segmenter_returns_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mod, "_segment", lambda _text: {"sec_relatorio": [[0, 3]]})

    gold_chars, pred_chars, was_skipped = mod._process_row("abcdef", {"sec_relatorio": [[0, 3]]})

    assert was_skipped is False
    assert pred_chars == ["sec_relatorio", "sec_relatorio", "sec_relatorio", "O", "O", "O"]
    assert gold_chars == pred_chars


def test_process_row_reports_skipped_when_segmenter_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mod, "_segment", lambda _text: None)

    gold_chars, pred_chars, was_skipped = mod._process_row("abcdef", {"sec_relatorio": [[0, 3]]})

    assert was_skipped is True
    # A None result still degrades to an all-"O" prediction for metrics purposes.
    assert pred_chars == ["O"] * 6
    assert gold_chars == ["sec_relatorio", "sec_relatorio", "sec_relatorio", "O", "O", "O"]
