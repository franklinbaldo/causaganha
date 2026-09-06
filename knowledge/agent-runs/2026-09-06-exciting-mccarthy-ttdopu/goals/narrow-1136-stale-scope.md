---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-ttdopu-goal-narrow-1136-stale-scope"
run_id: "2026-09-06-exciting-mccarthy-ttdopu"
goal: "Determine whether issue #1136's remaining acceptance item ('stale' state, applied consistently across /processo, /publicacoes, /stats, /minhas-consultas) is a real cross-surface gap, and record the finding back on the issue so a future round does not re-investigate or wrongly force a shared 'stale' treatment onto surfaces where it does not apply."
rationale: "The prior round (s5c21a) left this as an open next-move candidate ('a dedicated stale visual treatment across all three surfaces hasn't been built yet and could be the next slice'), phrased as if it were simply the next #1136 slice to implement. Before implementing anything, this round checked whether the underlying data model actually supports the same concept on every surface: ProcessoLookup's staleness warning is tied to a specific snapshot generation timestamp (indice_processual.parquet); PublicationSearch queries DJEN live with no generation timestamp in its data model at all; SavedConsultations is a local bookmark list with no dataset; and /stats already has its own, differently-coded freshness signal (DJEN checker pipeline health via evaluateSourceFreshness, a genuinely different concept from snapshot age). Forcing a shared 'stale' component across all four would misrepresent surfaces that have no dataset-staleness concept, which is exactly the risk #1136 itself names ('tratar todos os erros como equivalentes')."
success_signal: "A comment is posted on #1136 recording, per surface, whether 'stale' applies and why, so the issue's remaining scope is accurately narrowed instead of implying a uniform next slice. No source code changes are made for this goal — the deliverable is the recorded finding, verifiable by reading the issue thread and comparing it against the cited file/line evidence."
status: "achieved"
---

# Goal: esclarecer o escopo de "stale" na #1136

Verificar, superfície por superfície, se o estado "stale" (dataset desatualizado) do critério de aceite da #1136 realmente se generaliza, e registrar a descoberta na própria issue — em vez de deixar a implicação (da rodada anterior) de que seria "a próxima fatia óbvia" sem essa checagem.
