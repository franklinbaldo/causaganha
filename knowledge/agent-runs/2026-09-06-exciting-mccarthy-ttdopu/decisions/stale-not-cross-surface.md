---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-ttdopu-decision-stale-not-cross-surface"
run_id: "2026-09-06-exciting-mccarthy-ttdopu"
goal_id: "2026-09-06-exciting-mccarthy-ttdopu-goal-narrow-1136-stale-scope"
question: "Should this round implement a shared 'stale' visual treatment across /processo, /publicacoes, /stats and /minhas-consultas, as the prior round's next_move suggested?"
choice: "No. Do not implement a shared 'stale' component/selector this round. Instead, verify per-surface applicability and post the finding back to #1136 as a scope-narrowing comment."
rationale: "Checked each surface's actual data model: ProcessoLookup's staleness warning (isDatasetStale, web/src/lib/processoCnj.ts) is derived from a snapshot generation timestamp specific to indice_processual.parquet. PublicationSearch queries DJEN live per-request (grepped its component source: no generated_at/dataset/snapshot reference exists at all). SavedConsultations holds only locally-stored bookmarks with no dataset concept. /stats already has its own freshness signal (evaluateSourceFreshness/freshnessDisplayLabel in web/src/lib/data/siteStatus.ts), which measures DJEN checker pipeline health, not snapshot age — a different concept that already has its own, already-shipped presentation (a Panda badge). Three of the four surfaces either have no equivalent concept or already have a different, adequate one; only ProcessoLookup has the specific 'old snapshot' warning #1136 seems to have had in mind. Building a shared 'stale' primitive now would mean inventing a generic concept to paper over surfaces that don't share it — exactly the risk #1136's own text warns against ('tratar todos os erros como equivalentes')."
---

# Decisão: "stale" não é uma lacuna transversal real

Cada superfície tem (ou não tem) o conceito de "snapshot desatualizado" por razões estruturais diferentes: `ProcessoLookup` consulta um parquet gerado periodicamente; `PublicationSearch` consulta o DJEN ao vivo; `SavedConsultations` não tem dataset; `/stats` já mede outra coisa (saúde do pipeline de checagem) com sua própria apresentação. Construir um componente genérico de "stale" agora seria abstração incorreta, não uma correção de inconsistência real.
