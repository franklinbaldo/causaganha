---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-e9r0mj-check-full-suite"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
command: "cd web && npx vitest run; npm run lint; npm run typecheck; uv run ruff check; uv run ruff format --check; uv run pytest -q tests/causaganha/processos/"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-e9r0mj-evidence-green-mapping-parity"
summary: "Full web vitest suite: 357/357 passing (up from 356 baseline). eslint clean. astro typecheck: 19 errors/0 warnings/3 hints, identical to the pre-round baseline (no new errors from this diff). ruff check/format --check: clean, Python untouched aside from scripts/processo_query_plan_compare.py which passes ruff cleanly. tests/causaganha/processos/: 32/32 passing. An incidental, unrelated web/src/lib/djen-zod.gen.ts regeneration drift (orval version bump from a stale lockfile vs. committed codegen output, zod.number()->zod.int()) surfaced from `npm ci` and was reverted via `git checkout --` before committing, since it is unrelated to #1107 and out of this round's scope."
---
