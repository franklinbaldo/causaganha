---
type: "RunCheck"
id: "run-checks/20260910t092514z-do-the-best-useful-work-availab/check-verification"
run: "runs/20260910T092514Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "npm ci (789 packages) then npx vitest run src/lib/tribunalOgImage.test.ts src/pages/publicacoes (RED then GREEN, see evidence-red-green-ogimage) then npm run lint then npm run typecheck then npm test (full vitest, 72 files / 513 tests) then uv run ruff check then uv run ruff format --check then uv run pytest -q (full suite, 1 pre-existing skip)"
result: "pass"
status: "pass"
evidence: "run-evidence/20260910t092514z-do-the-best-useful-work-availab/evidence-red-green-ogimage"
goal: "run-goals/20260910t092514z-do-the-best-useful-work-availab/goal-audit-astro-pages"
---

# RunCheck
