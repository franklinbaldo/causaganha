---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-ich5gz-reading-okf"
run_id: "2026-09-05-exciting-mccarthy-ich5gz"
subject: "okf_knowledge"
reference: "knowledge/okf.schema.sql (full); knowledge/agent-runs/index.md; knowledge/agent-runs/2026-09-05-* (6 prior rounds today: eager-wozniak-5akx2o, exciting-mccarthy-{1fxd8b,9xpeua,e9r0mj,ejibsp,qvwrkl}); knowledge/contracts/*.md, knowledge/pipelines/*.md, knowledge/sources/*.md directory listing"
finding: "okf.schema.sql defines the product OKF tables (Fonte/Pipeline/DjenResumo/JurisDecisao/StjAcordao/DatajudCapa/Processo/FonteCobertura/DocumentoProcesso) plus the six session-report Agent* tables (AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck) with explicit CHECK/NOT NULL constraints on every field — read in full to mirror exactly in this round's own report frontmatter. knowledge/contracts/ holds the product-facing OKF docs (processo.md, fonte-cobertura.md, documento-processo.md, processo-ausente.md, djen-resumo.md, juris-decisao.md, stj-acordao.md, datajud-capa.md) — these describe the SAME shared-core shape that #1107's parity harness cross-checks between Python and Web, so any change to the availability semantics this round touches should stay consistent with fonte-cobertura.md's documented FonteCobertura.status contract (currently a free-text string, still not narrowed per prior round's next_move note — out of scope this round, not touched). Of today's 6 prior rounds, all reached result_state 'merged' or 'green' except none failed; the completeness checker (scripts/check_agent_run_completeness.py) and its CI wiring (added by round 'ejibsp') are the enforcement mechanism for this very report — running it against this round's own tree at each material step, per the scaffold's instructions, is how I will pace this session."
---

# Leitura de conhecimento OKF

Confirma o schema exato dos seis tipos `Agent*` (com todas as CHECK constraints) e o estado dos `contracts/` de produto relevantes a #1107 (FonteCobertura.status). Nenhuma rodada anterior hoje ficou bloqueada — todas fecharam `merged`/`green`, então não há um relatório `blocked` para retomar.
