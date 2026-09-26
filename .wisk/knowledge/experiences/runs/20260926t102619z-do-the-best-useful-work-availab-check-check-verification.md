---
type: "RunCheck"
id: "run-checks/20260926t102619z-do-the-best-useful-work-availab/check-verification"
run: "runs/20260926T102619Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full suite); uv run ruff check; uv run ruff format --check; uv run okf-parser check knowledge --relational-schema okf.schema.sql; uv run python scripts/segmenter_governance_status.py; uv run python scripts/segmenter_semantic_audit.py"
result: "Full pytest suite: all tests passed, exit code 0 (462 files, no failures). ruff check: all checks passed. ruff format --check: 462 files already formatted. okf-parser: conformant, 0 diagnostics (2579 concepts / 2582 markdown files). segmenter_governance_status.py: document_count=197, annotation_count=268, review_count=45, val_count=30 (ceiling), test_count=15 (of 30 floor), meets_rfc_0012_split_floor=false -- matches the round's simulation exactly. segmenter_semantic_audit.py: 6 findings, unchanged from the pre-round baseline, none of the 5 new documents implicated."
status: "pass"
evidence: "run-evidence/20260926t102619z-do-the-best-useful-work-availab/evidence-1051-adjudication"
goal: "run-goals/20260926t102619z-do-the-best-useful-work-availab/goal-1051-adjudication-slice"
---

# RunCheck
