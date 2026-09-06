---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-488tov-check-web-suite"
run_id: "2026-09-06-exciting-mccarthy-488tov"
goal_id: "2026-09-06-exciting-mccarthy-488tov-goal-export-import-saved-consultations"
command: "cd web && npm run lint && npm run typecheck && npm run test"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-488tov-evidence-green-backup-tests"
summary: "lint: 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts files, unrelated to this change). typecheck (astro check): 0 errors, 0 warnings, 5 pre-existing hints unrelated to this change. test: 63 files, 487/487 passed (up from the pre-round baseline of 456/456 across 58 files — +19 new tests in 2 new files, +12 net in existing files from re-running unaffected suites)."
---

# Check: suíte web completa

`npm run lint`/`typecheck`/`test` no diretório `web/` — todos verdes.
