---
type: "RunEvidence"
id: "run-evidence/20260910t173357z-do-the-best-useful-work-availab/evidence-red-green-skipped-counter"
run: "runs/20260910T173357Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_evaluate_regex_segmenter.py"
summary: "scripts/evaluate_regex_segmenter.py's per-row loop coalesced pred_spans from None to {} at line 118-119, then checked 'if pred_spans is None' at line 126 to increment skipped -- the second check was unreachable since pred_spans could never still be None by that point. Confirmed _segment() (scripts/prepare_privacy_filter_dataset.py:307) can genuinely return None. Extracted a pure _process_row(texto, gold_spans) -> (gold_chars, pred_chars, was_skipped) helper that captures the None-check BEFORE the coalescing assignment, and updated main()'s loop to use it. RED: new tests/test_evaluate_regex_segmenter.py (2 tests) against the unmodified inline code (verified via git stash) -- AttributeError: module has no attribute _process_row (2 failed). GREEN after the fix: 2/2 passed, including the case that reproduces the original bug scenario (a monkeypatched _segment returning None) now correctly reporting was_skipped=True. ruff check + ruff format --check clean. Full uv run pytest -q (entire suite) green."
goal: "run-goals/20260910t173357z-do-the-best-useful-work-availab/goal-fix-skipped-counter"
---

# RunEvidence
