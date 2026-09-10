---
type: "RunEvidence"
id: "run-evidence/20260910t182322z-do-the-best-useful-work-availab/evidence-red-green-remove-warnings"
run: "runs/20260910T182322Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_ia_practicality_probe.py"
summary: "scripts/ia_practicality_probe.py's probe_parquet() declared result['warnings'] but never populated it, and main()'s report['warnings'] counter summed it, so both were permanently 0/empty -- flagged by a prior round as a lead needing a deliberate implement-or-remove decision (RunDecision decision-remove-dead-warnings-field: removed, since the two candidate warning conditions considered -- extra columns beyond MINIMAL_REQUIRED_COLUMNS, a hardcoded low-row-count threshold -- were rejected as noise/arbitrary rather than genuine signals). Wrote the file's first-ever tests: a fixture that monkeypatches IA_DOWNLOAD_BASE to a local tmp directory so DuckDB reads a real local Parquet fixture instead of touching archive.org. RED: test_probe_parquet_result_has_no_dead_warnings_field asserted 'warnings' not in result against the unmodified code -- failed, dict had the key. GREEN after removing result['warnings'], the 'if result[\"warnings\"]:' check, and report['warnings'] from both probe_parquet() and main(). A second new test (test_probe_parquet_flags_missing_required_columns) exercises the existing missing-columns hard-failure path for the first time, unaffected by this change. ruff check + ruff format --check clean. Full uv run pytest -q (entire suite, including the 2 new tests) green."
goal: "run-goals/20260910t182322z-do-the-best-useful-work-availab/goal-decide-ia-probe-warnings"
decision: "run-decisions/20260910t182322z-do-the-best-useful-work-availab/decision-remove-dead-warnings-field"
---

# RunEvidence
