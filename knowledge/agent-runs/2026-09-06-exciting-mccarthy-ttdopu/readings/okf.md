---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-ttdopu-reading-okf"
run_id: "2026-09-06-exciting-mccarthy-ttdopu"
subject: "okf_knowledge"
reference: "uv run okf-parser check knowledge --relational-schema okf.schema.sql (run immediately after this round's three prior readings)"
finding: "Bundle conformant at the start of this round (concept_count=284 across all typed records, per prior round s5c21a's own final check reported 0 diagnostics after PR #1183/#1184 merged). Running the checker right after adding this round's three readings (claude-md, issues, prs) reports exactly the expected OKF022 dangling-foreign-key diagnostic on all three (AgentReading.run_id points at this round's AgentRun, which does not exist yet) — the scaffold's own operating instruction confirmed working as designed. 13 prior completed AgentRun reports exist under knowledge/agent-runs/ for 2026-09-05/06. The most recent (s5c21a) closed out the deferred web/UX backlog unblocking by extending query-states.css to /minhas-consultas and left two explicit next-move pointers: (1) a 'stale' visual treatment across surfaces as a possible next #1136 slice, and (2) CLAUDE.md's CSS-token-boundary staleness, flagged again but not fixed, 'left as a candidate for a future round'. This round's other two readings resolved pointer (1) by determining it does not generalize as a real gap (see decision + #1136 comment) and resolved pointer (2) by fixing it directly instead of deferring it a fifth time."
---

# Leitura do conhecimento OKF

Bundle conformante ao início da rodada (284 conceitos). O check logo após as três leituras iniciais mostra exatamente a lacuna de FK esperada pelo scaffold. As duas pontas deixadas pela rodada anterior (s5c21a) — tratamento visual de "stale" entre superfícies e a fronteira CSS desatualizada do CLAUDE.md — foram ambas resolvidas nesta rodada: a primeira por não ser, de fato, uma lacuna real (investigação registrada como decisão e devolvida à issue #1136); a segunda corrigida diretamente no CLAUDE.md em vez de adiada de novo.
