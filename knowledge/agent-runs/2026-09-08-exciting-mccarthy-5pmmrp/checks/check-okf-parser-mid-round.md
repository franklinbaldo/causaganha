---
type: AgentCheck
id: "2026-09-08-exciting-mccarthy-5pmmrp-check-okf-parser-mid-round"
run_id: "2026-09-08-exciting-mccarthy-5pmmrp"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Run after linking the goal, decision, and evidence/check files above. First pass hit OKF022 (foreign-key error): check-okf-parser-baseline.md had `evidence_id: \"\"`, which the schema reads as a pending FK reference, not absence -- the same known pitfall the two most recent prior rounds (14x3v7, kfv7sx) each independently hit and fixed the same way. Fixed by omitting the field entirely rather than leaving it empty. Re-ran: conformant=true, 0 diagnostics, 881 concepts (up from 870 at round start)."
---

# Check: okf-parser no meio da rodada

Ao vincular goal/decisão/evidências, bati no mesmo erro de FK que rodadas anteriores (14x3v7, kfv7sx) já haviam documentado: `evidence_id: ""` é lido como referência pendente, não ausência. Corrigido omitindo o campo. Nova rodada: conformante, 0 diagnósticos, 881 conceitos.
