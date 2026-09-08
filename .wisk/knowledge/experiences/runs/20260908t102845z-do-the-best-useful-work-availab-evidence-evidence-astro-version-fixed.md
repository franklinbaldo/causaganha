---
type: "RunEvidence"
id: "run-evidence/20260908t102845z-do-the-best-useful-work-availab/evidence-astro-version-fixed"
run: "runs/20260908T102845Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "CLAUDE.md:10, FRONTEND.md Tech Stack Overview table, README.md:186"
summary: "Changed 'Astro 5' to 'Astro 7' in all three live docs. Verified web/package.json pins astro ^7.1.3 and 'cd web && npx astro --version' prints 'astro v7.1.3', confirming the fix matches the real installed version. grep -rl 'Astro 5' --include=*.md . (excluding knowledge/agent-runs/, which is a frozen historical archive per its own index.md and must not be edited) returns zero remaining live matches."
goal: "goal-fix-astro-version-drift"
---

# RunEvidence
