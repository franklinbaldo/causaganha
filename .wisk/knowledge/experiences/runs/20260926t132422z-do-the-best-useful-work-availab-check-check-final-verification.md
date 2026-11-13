---
type: "RunCheck"
id: "run-checks/20260926t132422z-do-the-best-useful-work-availab/check-final-verification"
run: "runs/20260926T132422Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q tests/segmenter_dataset (full, 366+ tests); uv run pytest -q (full suite, ~2050 tests); uv run ruff check; uv run ruff format --check; uv run okf-parser check knowledge --relational-schema okf.schema.sql; uv run python scripts/segmenter_governance_status.py; uv run python scripts/segmenter_semantic_audit.py -- all run after the 3 new reviews were ingested."
result: "tests/segmenter_dataset: all green. Full pytest suite: exit 0, 1 pre-existing skip, 0 failures. ruff check/format --check: clean, 462 files. okf-parser check: conformant, 0 diagnostics, 2579 concepts. segmenter_governance_status.py: review_count=51, test_count=21, val_count=30 (matches pre-round simulation exactly). segmenter_semantic_audit.py: 6 findings, matching the pre-existing baseline exactly (no new document implicated after the mid-round long_anchor fix)."
status: "pass"
evidence: "https://github.com/franklinbaldo/causaganha/tree/claude/exciting-mccarthy-gakpa3"
goal: "run-goals/20260926t132422z-do-the-best-useful-work-availab/goal-1051-next-batch"
---

# RunCheck
