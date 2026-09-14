---
type: AgentCheck
id: "2026-09-14-exciting-mccarthy-bueov4-check-okf-parser-after-readings-goals-decisions"
run_id: "2026-09-14-exciting-mccarthy-bueov4"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-14-exciting-mccarthy-bueov4-evidence-review-pr-1483"
summary: "Detectou 8 erros OKF022 (foreign keys para AgentRun.id vazio) enquanto run.md.id ainda não estava preenchido; conformant: true, 0 diagnostics, concept_count: 1296, após preencher o cabeçalho de run.md."
---

# Check: okf-parser após leituras, goals e primeira decisão/evidência

Primeira rodada do check (logo após copiar o scaffold) reportou `conformant: true` mas com `run.md.id` ainda vazio -- lacuna esperada do scaffold. Após preencher as 4 leituras, os 2 goals e a primeira decisão sem ainda ter preenchido `id`/`goal_ids`/`decision_ids` no `run.md`, o check corretamente reportou `conformant: false` com 8 erros `OKF022` (foreign keys de `AgentReading`/`AgentGoal`/`AgentDecision`/`AgentEvidence` apontando para um `AgentRun.id` inexistente). Preenchido o cabeçalho do `run.md` com `id`, `started_at`, `branch_at_start`, `commit_at_start`, os quatro `*_reading_id`, `goal_ids`/`primary_goal_id`, `decision_ids` e `evidence_ids` parcial -- novo check retorna `conformant: true`, `0 diagnostics`, `concept_count: 1296`, confirmando que as referências cruzadas estão corretas antes de prosseguir para o merge dos PRs.
