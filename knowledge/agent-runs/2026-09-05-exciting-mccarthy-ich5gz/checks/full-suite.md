---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-ich5gz-check-full-suite"
run_id: "2026-09-05-exciting-mccarthy-ich5gz"
goal_id: "2026-09-05-exciting-mccarthy-ich5gz-goal-fonte-indisponivel-vs-ausente-parity"
command: "cd web && npx vitest run; cd .. && uv run pytest -q tests/causaganha/processos/; uv run ruff check; uv run ruff format --check; cd web && npx eslint src/lib/processoCnj.ts src/lib/processoQueryPlanParity.test.ts"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-ich5gz-evidence-green-availability-parity"
summary: "Full web vitest suite: 358/358 passing (up from 357 baseline). tests/causaganha/processos/: 32/32 passing. ruff check: all checks passed. ruff format --check: 1 file needed reformatting (scripts/processo_query_plan_compare.py, from the new tuple-return edits); reformatted with `uv run ruff format`, then re-verified clean and re-ran both test suites green. eslint on the two changed web files: no output, no errors."
---

# Check: suíte completa após a mudança

Vitest 358/358, pytest processos 32/32, ruff check/format limpos, eslint limpo.
