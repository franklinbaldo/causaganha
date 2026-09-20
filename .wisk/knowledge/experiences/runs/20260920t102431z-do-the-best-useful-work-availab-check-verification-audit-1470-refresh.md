---
type: "RunCheck"
id: "run-checks/20260920t102431z-do-the-best-useful-work-availab/verification-audit-1470-refresh"
run: "runs/20260920T102431Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q tests/test_audit_cnj_parquets.py; uv run ruff check; uv run ruff format --check; uv run okf-parser check knowledge --relational-schema okf.schema.sql; manual diff of new vs 2026-09-14 evidence file (item_id+table key set, classification transitions)"
result: "44/44 audit-script tests pass; ruff check/format clean repo-wide; okf-parser check on knowledge/ conformant (2031 concepts, 0 diagnostics); diff confirms 0 files lost, 0 unavailable/verify_values, 5 reorder_candidate->conformant transitions, 37 new conformant-at-publish files."
status: "pass"
evidence: "run-evidence/20260920t102431z-do-the-best-useful-work-availab/audit-refresh-2026-09-20"
goal: "run-goals/20260920t102431z-do-the-best-useful-work-availab/goal-refresh-1470-audit"
---

# RunCheck
