---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-8kw55y-reading-okf"
run_id: "2026-09-09-exciting-mccarthy-8kw55y"
subject: "okf_knowledge"
reference: "knowledge/index.md, knowledge/okf.schema.sql, knowledge/backlog/index.md, knowledge/agent-runs/2026-09-09-exciting-mccarthy-{pf1xhn,0lpi0s}/run.md"
finding: "okf.schema.sql defines 16 tables: 4 domain concepts (Fonte, Pipeline), 4 canonical data contracts (DjenResumo, JurisDecisao, StjAcordao, DatajudCapa, Processo, FonteCobertura, DocumentoProcesso), and the AgentRun session family (AgentRun, AgentReading, AgentGoal, AgentDecision, AgentEvidence, AgentCheck) plus BacklogItem for durable cross-round facts. This session family is stable -- no schema change requested by either of the two immediately preceding rounds (pf1xhn, 0lpi0s), both of which closed with result_state 'merged' and no open next_move debt beyond the two long-declined low-value leads (coverageInsights.ts dead code; djen.py 403 typing gap). Both prior rounds independently found and fixed a live production bug via a background Explore survey rather than the (exhausted) issue queue -- pf1xhn fixed render_queries.py's _register_tjro_juris/_register_datajud_capa missing IA-fallback, and its own CI fix for render_contract_fixture.py's real-network leak; 0lpi0s closed the structural gap pf1xhn flagged (unified network-isolation patching across all _register_* sources) and fixed a second latent monkeypatch-leak bug found while writing that fix's own regression test. This establishes the working pattern for the current round: since the issue/PR queue is exhausted (confirmed again this round, same 17 issues + unrelated Dependabot PR), source work via a fresh Explore survey rather than issue triage. No unresolved OKF-model gap identified by either prior round; the model is not obviously poor for representing this round's work, so no type/schema change is anticipated up front (will revisit if the selected goal doesn't fit cleanly)."
---

# Leitura de conhecimento OKF

Bundle estável: 16 tabelas cobrindo conceitos de domínio, contratos de dados canônicos e a família AgentRun/BacklogItem. As duas últimas rodadas (pf1xhn, 0lpi0s) fecharam limpo, sem dívida de schema pendente, e ambas encontraram trabalho via survey de código em vez da fila de issues esgotada -- padrão que esta rodada repete.
