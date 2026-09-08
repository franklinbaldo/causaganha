---
type: AgentCheck
id: "2026-09-08-exciting-mccarthy-2xmp5l-check-web-suite"
run_id: "2026-09-08-exciting-mccarthy-2xmp5l"
goal_id: "2026-09-08-exciting-mccarthy-2xmp5l-goal-delete-tribunal-calendar"
command: "npm ci && npx vitest run && npm run lint && npm run typecheck (all in web/)"
result: "passed"
evidence_id: "2026-09-08-exciting-mccarthy-2xmp5l-evidence-green-web-suite"
summary: "vitest: 65 test files, 491 tests, all passed — same file/test counts as before the deletion (no test imported TribunalCalendar.svelte). One transient failure on the first run (processoQueryPlanParity.test.ts's beforeAll hook shelling out to `uv run python ...` timed out at 10s while this environment's uv venv was still cold from the round's first okf-parser invocation); re-ran that single file once the venv was warm and it passed cleanly (4/4), then reran the full suite for a clean 65/65 green. eslint: 0 errors (43 pre-existing generated-file warnings, unrelated). astro check: 0 errors, 0 warnings, 5 pre-existing hints, unrelated. npm run typecheck's prebuild step regenerated web/src/lib/djen-zod.gen.ts with the same unrelated orval-version drift 14x3v7 already diagnosed and discarded (zod.number() -> zod.int(), version-comment change) — discarded again via `git checkout --` to keep this PR scoped to the actual change."
---

# Check: suíte web completa

Suíte completa (65 arquivos, 491 testes) verde após a exclusão. Uma falha transitória inicial (`processoQueryPlanParity.test.ts`, hook `uv run` a frio) não relacionada à mudança — confirmada como flake de ambiente reexecutando o arquivo isoladamente após o venv aquecer, depois reconfirmada com a suíte inteira. `eslint`/`astro check` limpos. Drift de codegen do orval (mesmo já visto na rodada anterior) descartado via `git checkout --`.
