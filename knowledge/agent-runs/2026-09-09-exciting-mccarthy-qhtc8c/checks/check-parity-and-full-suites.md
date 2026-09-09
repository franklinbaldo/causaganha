---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-qhtc8c-check-parity-and-full-suites"
run_id: "2026-09-09-exciting-mccarthy-qhtc8c"
goal_id: "2026-09-09-exciting-mccarthy-qhtc8c-goal-stj-date-cast-web-sql-twin"
command: "cd web && npx vitest run src/lib/processoQueryPlanParity.test.ts (real DuckDB execution of Python and JS SQL against shared fixtures, via `uv run python scripts/processo_query_plan_fixture.py`/`processo_query_plan_compare.py`); cd web && npx vitest run (full suite); npx tsc --noEmit; cd .. && uv run ruff check && uv run ruff format --check; uv run pytest -q"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-qhtc8c-evidence-green-and-diff"
summary: "processoQueryPlanParity.test.ts: 4/4 passed. Full web vitest: 71 files / 510 tests passed. tsc --noEmit: 3 pre-existing unrelated errors (import.meta.env typing in src/lib/data/index.ts, robots.txt.ts, sitemap.xml.ts -- confirmed via git diff --stat that this round touched none of those files). ruff check: all checks passed. ruff format --check: 406 files already formatted. pytest -q: only the pre-documented single failure from this run.md being in draft at check time (tests/test_check_agent_run_completeness.py), which resolves once completed_at/primary_goal_id/result_summary/next_move are filled -- no Python file touched by this round's JS-only fix, so no regression."
---

# Check: paridade cross-runtime + suites completas
