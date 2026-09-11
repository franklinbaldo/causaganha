---
type: "RunEvidence"
id: "run-evidence/20260911t042625z-do-the-best-useful-work-availab/evidence-red"
run: "runs/20260911T042625Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "cd web && npx vitest run src/lib/djen.test.ts (against unmodified djen.ts)"
summary: "RED: 4/5 pass, 1 fails -- normalizeExternalUrl('//evil.example.com/malware') returns 'https://evil.example.com/malware' instead of rejecting it, confirming the host-confusion defect from the Explore-agent sweep."
goal: "run-goals/20260911t042625z-do-the-best-useful-work-availab/goal-fix-normalize-external-url"
---

# RunEvidence
