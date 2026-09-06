---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-fpldz1-check-web-suite"
run_id: "2026-09-06-exciting-mccarthy-fpldz1"
goal_id: "2026-09-06-exciting-mccarthy-fpldz1-goal-continue-with-agent"
command: "cd web && npm test -- --run && npm run lint && npm run typecheck && npm run build"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-fpldz1-evidence-green-full-gate"
summary: "61 test files / 465 tests passed; lint 0 errors (43 pre-existing generated-file warnings, unchanged); typecheck (astro check) 0 errors, 0 warnings; build produced 109 pages against CI's own stubbed web/public/data/*.json. All stubs and dist/ deleted afterward; final diff clean."
---

# Check: suíte web completa

Executado após a integração do botão no componente, com stubs de dados idênticos aos usados pelo job `web` de `.github/workflows/test.yml`.
