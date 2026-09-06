---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-1na8o6-reading-okf"
run_id: "2026-09-06-exciting-mccarthy-1na8o6"
subject: "okf_knowledge"
reference: "knowledge/backlog/index.md; knowledge/agent-runs/2026-09-06-exciting-mccarthy-uwm65t/run.md (previous round); web/src/components/SavedConsultations.svelte, consultationSnapshot.ts, consultationSnapshotStore.ts, and their existing test suites (changeTracking/actions/keyboard)"
finding: "Prior round (uwm65t) closed issue #1217 and its explicit handoff was to re-read open issues fresh next round since a new one might appear. It did (#1232). Inspecting the current SavedConsultations.svelte confirmed the exact defect #1232 describes: checkForChanges() calls saveConsultationSnapshot(item.id, current) unconditionally after every comparison, including when compareConsultationSnapshots() returns 'mudou' or 'nao_comparavel' — so a second automatic check (e.g. simply reopening /minhas-consultas) silently advances the baseline to the just-observed (changed, or outage-degraded) state, making a real pending change disappear without any user acknowledgement, and — a second, related bug not named in the issue title but implied by its 'falha/indisponibilidade nunca avança baseline' requirement — corrupting the baseline with null source fields during a transient outage, which then makes a *subsequent* real change silently invisible too (a null-vs-null 'comparison' trivially resolves to sem_mudanca since baselineSourceCount stays 0). No OKF type/schema change is needed for this round's selected work; it is pure product code (Svelte component + its existing Vitest contract suite), matching the previous round's pattern for a small, well-scoped, no-external-blocker issue."
---

# Leitura do conhecimento OKF

A rodada anterior (uwm65t) fechou #1217 e indicou reler as issues abertas no início desta rodada — encontrou-se #1232. A inspeção do componente confirmou o defeito descrito e um segundo bug correlato (baseline corrompida por indisponibilidade transitória de fonte também esconde uma mudança real subsequente). Nenhuma mudança de schema OKF é necessária; o trabalho é código de produto (Svelte + testes Vitest já existentes no mesmo padrão).
