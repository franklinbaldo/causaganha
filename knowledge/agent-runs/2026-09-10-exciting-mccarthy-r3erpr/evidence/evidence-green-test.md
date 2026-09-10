---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-r3erpr-evidence-green-test"
run_id: "2026-09-10-exciting-mccarthy-r3erpr"
goal_id: "2026-09-10-exciting-mccarthy-r3erpr-goal-cb-probe-lock-order"
kind: "test_green"
reference: "uv run pytest tests/djen_backup/ -q, after reordering upload_zip's two guards in src/djen_backup/archive.py"
summary: "126 passed. New regression test passes (breaker stays HALF_OPEN after the ItemBusyError). All pre-existing djen_backup tests (locks, circuit breaker, upload worker, check-only, upload-only) stay green -- no behavior change for the non-busy path. Full repo suite: only the three expected draft-report failures remained before this run.md was filled in (tests/test_check_agent_run_completeness.py, tests/web/test_generate_okf_zod_schemas.py, tests/causaganha_mcp/test_okf_domain_models.py), not caused by the code fix. ruff check and ruff format --check both clean on the changed files."
---

# Evidência GREEN

`uv run pytest tests/djen_backup/ -q` -> 126 passed. `uv run ruff check` -> All checks passed. `uv run ruff format --check` -> limpo nos arquivos alterados.
