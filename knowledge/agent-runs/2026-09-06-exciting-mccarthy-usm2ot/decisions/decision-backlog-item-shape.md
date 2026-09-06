---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-usm2ot-decision-backlog-item-shape"
run_id: "2026-09-06-exciting-mccarthy-usm2ot"
goal_id: "2026-09-06-exciting-mccarthy-usm2ot-goal-backlog-cache"
question: "How should the 'blocked backlog' knowledge cache be modeled: as a new top-level OKF type (BacklogItem) with its own knowledge/backlog/ directory, or as an extension of the existing AgentRun-family types (e.g. a new AgentReading subject, or fields tacked onto AgentGoal)?"
choice: "New top-level type BacklogItem, PK issue_number, one markdown file per issue under knowledge/backlog/, independent of any single round's knowledge/agent-runs/<run-id>/ directory. FK last_verified_run_id -> AgentRun(id) links back to whichever round last confirmed the fact still holds."
rationale: "AgentReading/AgentGoal/etc. are scoped by design to a single run_id and physically live inside that run's own directory — that is exactly why the same 17-issue rejection gets re-derived every round: the fact dies with the round. A cross-round fact needs a home outside any one round's directory, which is precisely the pattern the existing domain concepts (Fonte, Processo, ...) already use: standalone files under knowledge/, referenced and updated by many rounds over time. Reusing the FK-to-AgentRun idiom (already used by AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck) keeps 'who last verified this' auditable without duplicating that mechanism."
---

# Decisão: BacklogItem como type de topo, não extensão da família AgentRun

Um fato que precisa sobreviver a várias rodadas não pode morar dentro do diretório de uma única rodada. `BacklogItem` segue o mesmo padrão dos conceitos de domínio (`Fonte`, `Processo`, ...): arquivo próprio em `knowledge/`, com FK para o `AgentRun` que fez a última verificação.
