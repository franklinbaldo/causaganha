---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-ejibsp-reading-okf"
run_id: "2026-09-05-exciting-mccarthy-ejibsp"
subject: "okf_knowledge"
reference: "knowledge/okf.schema.sql (AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck tables); scripts/check_agent_run_completeness.py (from PR #1144); .github/workflows/okf.yml"
finding: "knowledge/okf.schema.sql declares NOT NULL/CHECK constraints (required text fields, enum fields) on all six AgentRun-family tables, not just AgentRun. PR #1144's scripts/check_agent_run_completeness.py only mirrors AgentRun's contract (missing_agent_run_fields) and only ever validates a single explicit run.md path — the five sibling types (AgentReading, AgentGoal, AgentDecision, AgentEvidence, AgentCheck) have declared CHECK constraints that are exactly as unenforced by okf-parser 0.45.6 as AgentRun's were, and nothing in scripts/ or .github/workflows/okf.yml checks any of knowledge/agent-runs/**/*.md automatically — the completeness check is a manual step a round has to remember to run on its own report. This is precisely the next_move PR #1144 itself recorded: extend the same completeness contract to the sibling types and wire it into CI."
---

# Leitura de conhecimento OKF

O contrato SQL cobre as seis tabelas `Agent*`, mas o checador de completude só cobre `AgentRun` e só roda manualmente sobre um arquivo. Duas lacunas concretas e testáveis: (1) `AgentReading`/`AgentGoal`/`AgentDecision`/`AgentEvidence`/`AgentCheck` não têm checagem de completude equivalente; (2) nenhum workflow de CI valida `knowledge/agent-runs/**/*.md` automaticamente, então uma rodada futura pode fechar um relatório incompleto sem que nada acuse isso antes do merge.
