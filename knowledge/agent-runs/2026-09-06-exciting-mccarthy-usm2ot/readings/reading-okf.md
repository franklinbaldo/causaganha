---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-usm2ot-reading-okf"
run_id: "2026-09-06-exciting-mccarthy-usm2ot"
subject: "okf_knowledge"
reference: "knowledge/okf.schema.sql; knowledge/agent-runs/index.md; .claude/hourly-loop.md; uv run okf-parser check knowledge --relational-schema okf.schema.sql (427 concepts, 0 diagnostics, before this round's own report existed)"
finding: "knowledge/ models two families: product-domain concepts (Fonte, Pipeline, Processo, DjenResumo, JurisDecisao, StjAcordao, DatajudCapa, FonteCobertura, DocumentoProcesso) and the AgentRun family that drives this hourly loop (AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck). Neither family has a place to record a durable, cross-round fact like 'issue #1022 is blocked on absent IA credentials, last verified on date X by run Y' — every round's AgentReading is scoped to run_id and lives only inside that round's own directory, so the finding dies with the round and the next round re-derives it from the GitHub issue tracker alone. This is exactly the gap round 6x90uc's next_move named (a 'blocked backlog' cache) and round m65xwe's next_move repeated without resolving. Decision: model this as a new top-level type, BacklogItem (PK issue_number, FK last_verified_run_id -> AgentRun), stored one file per issue under knowledge/backlog/, independent of the per-round agent-runs tree — the same architectural pattern already used for domain concepts (Fonte, Processo, ...), which also live outside any single run's directory and get referenced/updated across rounds."
---

# Leitura do conhecimento OKF

Nenhuma das duas famílias de tipos hoje modela um fato que precisa sobreviver a mais de uma rodada: "esta issue está bloqueada, por este motivo, verificado pela última vez nesta rodada". Cada `AgentReading` está preso ao `run_id` da sua própria rodada. Essa é exatamente a lacuna que as rodadas 6x90uc e m65xwe já haviam nomeado em seus `next_move` sem resolver. Decisão: criar o type `BacklogItem` (chave primária `issue_number`, FK `last_verified_run_id` para `AgentRun`), guardado em `knowledge/backlog/`, um arquivo por issue — mesmo padrão arquitetural dos conceitos de domínio (`Fonte`, `Processo`, ...), que também vivem fora da árvore de qualquer rodada específica.
