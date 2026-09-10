---
type: "RunGoal"
id: "run-goals/20260910t132702z-do-the-best-useful-work-availab/goal-annotate-llm-adr-citation"
run: "runs/20260910T132702Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Close the docs/adr/0011 citation gap in scripts/annotate_with_llm.py's two per-item LLM-call bulkheads (annotate_batch at line 449, annotate_text at line 489): both already log the full traceback via logger.exception(...) before returning a failure sentinel to their per-batch/per-doc caller loop -- structurally identical to the four sites ADR 0011 already blesses -- but sit in scripts/, outside tests/test_except_exception_policy.py's src/-only scan, and lack the one-line ADR citation CLAUDE.md's 'No blind except Exception' rule requires of any new bulkhead site."
rationale: "An Explore-agent audit (this round) plus a direct repo-wide grep for 'except Exception' confirmed these two sites already satisfy ADR 0011's substantive bulkhead test (per-item work inside a loop, full traceback logged) but are missing the required citation, and that the existing enforcement test only scans src/, so this real, narrow, mechanically-verifiable gap was never caught. Scoping to just this one already-identified file (not a full scripts/ sweep) is a deliberate choice: the same grep found ~23 more bare except-Exception sites across 8 other scripts/ files, several already carrying inline '# noqa: BLE001' reasoning instead of an ADR citation, each needing its own bulkhead-vs-narrow judgment call outside this round's scope."
success_signal: "tests/test_except_exception_policy.py gains a new test asserting both scripts/annotate_with_llm.py:449 and :489 cite docs/adr/0011; it fails RED on the current file (no citation) and passes GREEN after adding the one-line comment at both sites, with the full pytest suite, ruff check, and ruff format --check all staying green."
status: "active"
---

# RunGoal
