---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-k18r9l-adr-reading-okf"
run_id: "2026-09-08-exciting-mccarthy-k18r9l-adr"
subject: "okf_knowledge"
reference: "knowledge/index.md; docs/adr/ (existing ADR 0010); knowledge/agent-runs/2026-09-08-exciting-mccarthy-k18r9l/run.md and its predecessors (1c7t6u, b4t8pv)"
finding: "Bundle shape unchanged (4 sources, 4 pipelines, 8 contracts, 1 projection, 18 backlog). Read this session's own immediately prior round (k18r9l) plus the two rounds before it in the same lineage (1c7t6u, b4t8pv) to confirm the except-Exception/BLE001 gap's exact history: first surfaced by 1c7t6u's Explore-subagent survey, re-confirmed unaddressed by b4t8pv, re-confirmed unaddressed again by k18r9l's own next_move -- three consecutive rounds logging the identical lead as 'needs a human decision' without ever escalating it or deciding it. The repo's docs/adr/ directory (outside the knowledge/ OKF bundle, in docs/) already holds one prior ADR (0010, standard Nygard format) for the segmenter pipeline rebuild -- confirming ADRs are an established, if underused, decision-record mechanism in this repo distinct from the OKF AgentDecision type (which is scoped to one round's own reasoning, not a durable cross-round architecture record). Baseline okf-parser check (before this round's own readings existed) inherited from k18r9l's final state: conformant, 854 concepts, 0 diagnostics."
---

# Reading: knowledge OKF bundle e docs/adr

Historico do gap except-Exception/BLE001 confirmado em 3 rodadas anteriores sem decisao. `docs/adr/` ja existe com uma entrada previa (0010) no formato Nygard padrao -- mecanismo pronto para registrar esta decisao como algo durador, distinto do `AgentDecision` OKF (que e escopado a uma rodada).
