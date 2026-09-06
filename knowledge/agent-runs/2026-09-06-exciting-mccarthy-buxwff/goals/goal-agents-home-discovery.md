---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-buxwff-goal-agents-home-discovery"
run_id: "2026-09-06-exciting-mccarthy-buxwff"
goal: "Make the /agentes MCP surface discoverable from the home page and the site's always-visible navigation, closing issue #1219, without weakening Processo/Publicações as the primary human entries."
rationale: "#1219, filed by the repo owner minutes before this round started and marked READY, is the only open issue with no external blocker — the other 17 open issues are all recorded in knowledge/backlog/ as blocked on credentials, an infra/hosting decision, or explicit owner deprioritization. It directly follows #1217/#1218 (merged this same day): the /agentes page itself is now actionable, but the home page still only advertises 'Duas entradas principais' and buries Agentes inside the 'Mais' dropdown, so a person who doesn't already know the MCP surface exists has no way to find it."
success_signal: "web/src/layouts/Layout.astro's always-visible primary nav (not just the 'Mais' menu) includes an Agentes link with the same aria-current wiring as Processo/Publicações/Salvos, verified by a new Vitest contract test (Layout.agentsNav.test.ts) that fails (RED) before the change because the link only exists inside the 'Mais' <details> block, and passes (GREEN) after; the public footer links to /agentes (same test file); web/src/pages/index.astro offers a visible CTA to /agentes and text making clear an agent queries the same archive, not a parallel API, verified by a second new Vitest contract test (_index.agentsCta.test.ts, RED before/GREEN after) that also regression-checks Processo/Publicações remain present and that no remote MCP URL is announced; a real Chromium build+serve+screenshot at 1280x900 and 390x844 shows zero horizontal scroll overflow at both viewports and confirms the CTA/footer link are visually legible (not the invisible-outline-button bug found and fixed during this round); npm run lint/typecheck/test and ruff check/format/pytest -q all stay green except this round's own report-completeness test, which turns green once this file's required fields are filled in."
status: "achieved"
---

# Goal: descoberta pública de /agentes a partir da home (#1219)

Tornar `/agentes` uma entrada de primeira classe na navegação e na home, sem enfraquecer `Processo`/`Publicações` como entradas humanas principais, fechando #1219.
