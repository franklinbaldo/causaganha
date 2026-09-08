---
type: "RunCheck"
id: "run-checks/20260908t052521z-do-the-best-useful-work-availab/check-web-suite-green"
run: "runs/20260908T052521Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "cd web && npm run test -- --run && npm run typecheck && npm run lint && npm run build (after uv run python scripts/render_queries.py); plus grep -rn 'fetchAllData|deriveData(|startLivePolling|getArchiveSnapshot|useDashboardWithPolling|useDashboard.svelte|buildTimeData|DerivedData|CacheData' web/src FRONTEND.md"
result: "66 test files / 493 tests passed; astro check reported 0 errors/0 warnings/5 pre-existing hints; eslint reported 0 errors (only pre-existing generated .d.ts warnings); astro build produced 120 pages with no errors; the grep for every removed symbol returned zero matches repo-wide. Reverted unrelated codegen drift (og/*.svg, djen-zod.gen.ts) picked up incidentally by npm ci/build so the diff stays scoped to the goal."
status: "pass"
evidence: "run-evidence/20260908t052521z-do-the-best-useful-work-availab/evidence-diff-remove-dead-architecture"
goal: "run-goals/20260908t052521z-do-the-best-useful-work-availab/goal-remove-dead-dashboard-fetch-architecture"
---

# RunCheck
