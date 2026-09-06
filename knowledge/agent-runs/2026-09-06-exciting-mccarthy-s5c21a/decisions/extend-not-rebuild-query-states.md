---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-s5c21a-decision-extend-not-rebuild-query-states"
run_id: "2026-09-06-exciting-mccarthy-s5c21a"
goal_id: "2026-09-06-exciting-mccarthy-s5c21a-goal-1136-minhas-consultas-query-states"
question: "How should #1136's shared query-state vocabulary reach the third surface (/minhas-consultas / SavedConsultations.svelte): extend the existing web/src/styles/query-states.css selectors, build a new shared component/primitive, or duplicate the rules into a SavedConsultations-scoped stylesheet?"
choice: "Extend the existing selector list in query-states.css to include .saved-consultations alongside .processo-lookup/.publication-search. No new component, no duplicated stylesheet, no change to SavedConsultations.svelte's own markup."
rationale: "Live inspection showed SavedConsultations.svelte already emits the exact same semantic markers (class=\"empty-state\", role=\"alert\", aria-busy=\"true\") that query-states.css already keys off of for the other two surfaces — the only gap was that .saved-consultations was missing from the :where() selector lists. #1136's own text explicitly warns against 'criar componente genérico demais que apaga contexto específico' and prefers 'duas ou três primitivas claras a um componente genérico com dezenas de props'. A new shared <QueryState> wrapper component would be premature abstraction from a single prior slice (#1164); duplicating the CSS into a second stylesheet would just re-create the same rules with a new maintenance burden. Extending the existing, already-parameterized selector is the minimal change that closes the actual gap (layout-stability guarantees) without inventing new abstractions or touching the component's own semantic state machine."
---

# Decisão: estender seletor existente, não criar novo componente

`query-states.css` já é parametrizado por seletor (`:where(.processo-lookup, .publication-search) ...`). Como `SavedConsultations.svelte` já usa os mesmos marcadores semânticos das duas superfícies cobertas, a extensão mínima e correta é adicionar `.saved-consultations` a cada grupo de seletor existente — não criar um componente genérico novo nem duplicar CSS.
