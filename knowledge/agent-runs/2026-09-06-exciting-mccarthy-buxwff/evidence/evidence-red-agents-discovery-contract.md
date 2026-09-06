---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-buxwff-evidence-red-agents-discovery-contract"
run_id: "2026-09-06-exciting-mccarthy-buxwff"
goal_id: "2026-09-06-exciting-mccarthy-buxwff-goal-agents-home-discovery"
kind: "test_red"
reference: "npx vitest run src/layouts/Layout.agentsNav.test.ts src/pages/index.agentsCta.test.ts, run against Layout.astro/index.astro before any #1219 change"
summary: "5 of 7 new assertions failed as expected before implementation: Layout.agentsNav.test.ts's 'Agentes in always-visible primary nav' and 'no duplicate inside Mais' failed because the only Agentes link lived inside the <details>/'Mais' block; the footer-link assertion failed because the footer only linked Processo/Publicações/Sobre. index.agentsCta.test.ts's CTA-presence and 'mesmo acervo' assertions failed because index.astro had no /agentes reference at all. The 2 passing assertions (Processo/Publicações still present, no remote MCP URL) were trivially true pre-change and served as a regression guard, not proof of the new behavior."
---

# Evidência RED: contrato de descoberta de /agentes

`Test Files 2 failed (2)` / `Tests 5 failed | 2 passed (7)` antes de qualquer mudança em `Layout.astro`/`index.astro` — confirma que os testes exercitam comportamento ainda inexistente.
