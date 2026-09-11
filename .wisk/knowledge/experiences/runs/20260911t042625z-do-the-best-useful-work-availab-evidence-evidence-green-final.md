---
type: "RunEvidence"
id: "run-evidence/20260911t042625z-do-the-best-useful-work-availab/evidence-green-final"
run: "runs/20260911T042625Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "cd web && npx vitest run src/lib/djen.test.ts (against the final origin-check implementation, commit 74226c4); then full suite + eslint + astro check"
summary: "GREEN on the final diff: djen.test.ts 6/6 pass (adds the backslash network-path regression case a Codex review found after evidence-green was first recorded, which the origin === djenBase check -- not the earlier '//' prefix blacklist -- rejects correctly). Full web suite: 73 files / 524 tests pass, no regressions. eslint clean on djen.ts/djen.test.ts. astro check: 0 errors, 0 warnings (5 pre-existing hints unrelated to this change). Supersedes evidence-green, which reported 5/5 and 523 tests against the intermediate '//'-blacklist-only implementation before the backslash bypass was found and fixed."
goal: "run-goals/20260911t042625z-do-the-best-useful-work-availab/goal-fix-normalize-external-url"
---

# RunEvidence
