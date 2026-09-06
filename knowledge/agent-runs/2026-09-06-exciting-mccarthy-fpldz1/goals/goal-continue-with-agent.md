---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-fpldz1-goal-continue-with-agent"
run_id: "2026-09-06-exciting-mccarthy-fpldz1"
goal: "Implement issue #1225: in ProcessoLookup.svelte's 'found' state, add a 'Continuar com um agente' action that copies a natural-language question containing the exact CNJ just consulted, built by a new single-authority TypeScript function with its own tests, plus a secondary onboarding link to /agentes — with no network call and no MCP tool names in the copied text."
rationale: "Issue #1225 is the only unblocked, issue-tracked, owner-authored, 'READY para IMPLEMENTAÇÃO' work available this round (the other 17 open issues are all confirmed still blocked in knowledge/backlog/, and there is no open PR to continue). It closes a real discoverability gap the owner named explicitly: /processo and /agentes already point at the same Processo domain root (knowledge/projections/processo-consultar.md) and the same MCP tool catalog (#1217/#1219), but a person who just looked up a CNJ on the site has no way to hand that same CNJ to a connected agent without manually retyping it after navigating away."
success_signal: "A new web/src/lib/agentContinuationQuestion.ts (or equivalent) exports the single wording authority, exercised by its own unit tests that assert exact CNJ interpolation, task-only language (no MCP tool name, no JSON) and mention of provenance/date/ausência-vs-indisponibilidade; ProcessoLookup.svelte's found-state action bar gains a button that copies this text to the clipboard with accessible aria-live feedback distinct from 'Link copiado'/'Referência copiada', plus a secondary link to /agentes, verified by new component tests that assert the three copy actions (permalink/reference/agent question) produce semantically distinct text; the full web gate (npm test, lint, typecheck, build) stays green with no regression; a PR is opened against main and, if CI passes, merged."
status: "achieved"
---

# Goal: continuar a consulta no agente com o CNJ já contextualizado

Implementação direta da issue #1225, seguindo TDD: testes da função de autoridade primeiro (RED), depois a função; testes do componente para a nova ação (RED), depois a integração no componente (GREEN); suíte completa antes de abrir a PR.
