---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-14x3v7-evidence-green-retry-after"
run_id: "2026-09-07-exciting-mccarthy-14x3v7"
goal_id: "2026-09-07-exciting-mccarthy-14x3v7-goal-djen-retry-after-floor"
kind: "test_green"
reference: "web/src/lib/djenClient.ts:304-308; web/src/components/__steps__/djen-search.steps.ts (9 tests)"
summary: "Replaced `throw new DjenRateLimitError(Math.max(60, retryAfterSec));` with `throw new DjenRateLimitError(retryAfterSec);` in web/src/lib/djenClient.ts's unwrap(). `npx vitest run src/components/__steps__/djen-search.steps.ts` now passes all 9 tests (the new one plus the pre-existing 90s-floor case, which stays green since 90 > 60 was never affected by the floor). Full web suite: `npx vitest run` — 65 test files, 491 tests, all passed. `npm run lint` (eslint) — 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts files unrelated to this diff). `npm run typecheck` (astro check) — 0 errors, 0 warnings, 5 pre-existing hints unrelated to this diff."
---

# Evidência GREEN

```
Test Files  1 passed (1)
     Tests  9 passed (9)
```

Suite completa web:
```
Test Files  65 passed (65)
     Tests  491 passed (491)
```

`eslint .`: 0 errors. `astro check`: 0 errors, 0 warnings, 5 hints pré-existentes.
