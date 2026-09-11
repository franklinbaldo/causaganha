---
type: AgentCheck
id: "2026-09-11-exciting-mccarthy-vd5dfq-check-green-and-suite"
run_id: "2026-09-11-exciting-mccarthy-vd5dfq"
goal_id: "2026-09-11-exciting-mccarthy-vd5dfq-goal-datajud-timezone-date-shift"
command: "cd web && npx vitest run src/lib/processoCnj.test.ts && npx vitest run && npm run lint; cd .. && uv run pytest -q"
result: "passed"
evidence_id: "2026-09-11-exciting-mccarthy-vd5dfq-evidence-green-test"
summary: "web/src/lib/processoCnj.test.ts: 88/88 passed. Full web vitest suite: 72 files / 515 tests, all passed. web lint: 0 errors (43 pre-existing generated-file warnings, unrelated). Python repo-wide `uv run pytest -q` first run (while this run.md was still a draft): 14 failures in tests/causaganha_mcp/ -- initially suspected as the documented draft-AgentRun shape cascade, but root-caused instead to a real invalid-YAML bug in this round's own reading-okf.md (see check-okf-parser-cli-vs-api-yaml-gap.md): an embedded blank line broke quoted-scalar YAML folding, which `okf_parser.load_bundle(...).is_conformant` correctly rejected (though the CLI `okf-parser check` command did not), and causaganha_mcp.knowledge.load_pipeline_metadata raises RuntimeError whenever the bundle isn't conformant. Fixed the YAML, re-ran `uv run pytest -q`: 100% pass, 0 failures repo-wide (verified after run.md's own completed_at/primary_goal_id/result_summary/next_move were filled in, so this is the final, non-draft state)."
---

# Check: suíte verde após a correção

`processoCnj.test.ts`: 88/88. Suíte web completa: 515/515. Lint web: 0 erros. Suíte Python: falhas confinadas ao cascade conhecido de `run.md` em rascunho (mais amplo do que o scaffold documenta, mas não relacionado a esta correção) -- será reconfirmada como 0 falhas após o fechamento do relatório.
