---
goal: "Fix scripts/evaluate_regex_segmenter.py's dead 'skipped' counter: pred_spans is coalesced from None to {} before the None-check that increments skipped, making the check permanently unreachable. Extract a testable _process_row helper and fix the ordering, then add a RED->GREEN test."
id: "run-goals/20260910t173357z-do-the-best-useful-work-availab/goal-fix-skipped-counter"
kind: "task-advance"
rationale: "Reading scripts/evaluate_regex_segmenter.py end-to-end (the long-tail defect audit named by PR #1408's next_move, now the loop's stated next body of work per the just-closed except-Exception lineage) found this dead-code bug on line 118-126: pred_spans = _segment(texto); if pred_spans is None: pred_spans = {} ... later if pred_spans is None: skipped += 1 -- the second check can never be true since pred_spans was already reassigned. This silently hides every text the regex segmenter failed to produce ANY segmentation for, and those texts still get scored as complete misses in the precision/recall/F1 metrics with no visibility that the miss was a segmenter failure rather than a labeling disagreement."
run: "runs/20260910T173357Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A failing test demonstrates _segment returning None currently produces skipped=0 (bug) via the extracted helper; after the fix, the same scenario returns was_skipped=True; full ruff+pytest green; PR opened."
type: "RunGoal"
---

# RunGoal
