---
type: "RunCheck"
id: "run-checks/20260920t094145z-do-the-best-useful-work-availab/check-ruff-pytest-okf-batch25"
run: "runs/20260920T094145Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check; uv run ruff format --check; uv run okf-parser check knowledge --relational-schema okf.schema.sql; uv run pytest -q tests/segmenter_dataset; uv run pytest -q (full suite)"
result: "All green. ruff check: All checks passed. ruff format --check: 454 files already formatted. okf-parser check: conformant, 0 diagnostics, 2031 concepts. pytest -q tests/segmenter_dataset: 100% pass (no F/E markers) after extending the semantic-audit false-positive allowlist with the 8th doc_id (TRF3/42491442, verified as a genuine false positive). Full uv run pytest -q: exit code 0, 100% pass across the whole repo (web, causaganha_mcp, djen_backup, segmenter_dataset, agent-run-completeness, OKF-generated-schema tests all included). Pushed commit bcf007b to origin/claude/exciting-mccarthy-hyn45b."
status: "pass"
evidence: "run-evidence/20260920t094145z-do-the-best-useful-work-availab/evidence-batch25-ingested"
goal: "run-goals/20260920t094145z-do-the-best-useful-work-availab/goal-djen-sample-batch25"
---

# RunCheck
