---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-tp38w3-decision-scope-processo-only-best-effort-fetch"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
goal_id: "2026-09-06-exciting-mccarthy-tp38w3-goal-mostrar-mudancas-desde-ultima-consulta"
question: "#1133's proposal text says 'ao salvar/reabrir um processo' (singular, about the /processo dossier). Should this round's snapshot/diff also cover type='busca' saved DJEN searches, and should a live-fetch failure ever block rendering the saved-consultations list?"
choice: "Scope this round strictly to type='processo' items — 'busca' saved searches (raw DJEN query params, no ProcessoConsultar-shaped dossier) are left untouched, matching the issue's own wording and #1105's shared-core contract, which only exists for the processo dossier. Every live check (checkForChanges) is wrapped in try/catch and never throws into the component: a getDuckDB()/buscarProcesso() failure degrades to an 'erro' verdict for that one item, the rest of the page (including 'busca' items, and adding/renaming/removing any consultation) keeps working exactly as before."
rationale: "Extending the comparison to 'busca' items would require inventing a second, undocumented notion of 'observable state' for a raw search (e.g. result count) that #1133 never asked for and that isn't backed by any shared OKF contract — a real drift risk the same way #1107 warns against duplicating semantics ad hoc. Making the live fetch best-effort/non-blocking preserves SavedConsultations.svelte's existing zero-network, always-available character for its core job (storing/reopening/renaming/removing local shortcuts) — the change-tracking badge is an enhancement layered on top, not a new hard dependency an existing user flow could break on."
---

# Decisão: só `type: 'processo'`, e a checagem nunca é bloqueante

`/minhas-consultas` continua funcionando por completo mesmo se a checagem de mudança falhar (DuckDB indisponível, fonte fora do ar): o pior caso é um veredito "não foi possível verificar", nunca uma página quebrada. Buscas DJEN salvas (`type: 'busca'`) ficam fora do escopo desta fatia — não há contrato de dossiê equivalente para elas.
