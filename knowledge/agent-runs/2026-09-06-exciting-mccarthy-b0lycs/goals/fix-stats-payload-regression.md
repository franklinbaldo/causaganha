---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-b0lycs-goal-fix-stats-payload-regression"
run_id: "2026-09-06-exciting-mccarthy-b0lycs"
goal: "Stop /stats from shipping the entire tribunal_calendar contract (~13.9MB, every tribunal × date in the archive) as a serialized prop to the client:only TribunalCoverageExplorer island. Replace it with build-time partitioned per-tribunal JSON artifacts, fetched client-side only for the currently selected tribunal, following the same filter-at-build-time pattern already used by web/src/pages/publicacoes/[tribunal].astro."
rationale: "Issue #1191 (filed by the owner right after the previous round's PR #1189 merged) identifies this as a high-priority regression: client:only islands serialize their props into the page for hydration, so the full global calendar currently ships to every /stats visitor even though the drill-down UI only ever renders one tribunal's days at a time. The issue names the exact healthier precedent already in this codebase to follow, and requires the fix to preserve #1131's behavior (uploaded/absent/sem_evidencia semantics, shareable URL, parity with the canonical contract) while adding an explicit regression gate so the payload cannot silently balloon back to global size."
success_signal: "TribunalCoverageExplorer.svelte no longer declares a bulk calendarRows prop; it fetches only the selected tribunal's partition on demand (verified by a component test asserting fetch is called with a per-tribunal URL, never the global tribunal_calendar.json). stats.astro still reads the full contract at build time (server-only, zero client cost) solely to write the per-tribunal partitions and no longer passes it as an island prop. A new grep-based regression test fails if the full-array prop reappears. #1131's existing behavior (uploaded/absent/sem_evidencia, coveragePct=null when unobserved, shareable tribunal/start/end URL, parity with the canonical contract) is unchanged and covered by tests. npm test, npm run lint, npm run typecheck and npm run build (with the CI's stub data files) all pass. A PR closing #1191 is opened."
status: "achieved"
---

# Goal: corrigir a regressão de payload em /stats (#1191)

Substituir a prop `calendarRows` (contrato `tribunal_calendar` inteiro, ~13,9MB) por artefatos particionados por tribunal, gerados em build-time e buscados no cliente só para o tribunal selecionado — seguindo o padrão já saudável de `/publicacoes/[tribunal]`.
