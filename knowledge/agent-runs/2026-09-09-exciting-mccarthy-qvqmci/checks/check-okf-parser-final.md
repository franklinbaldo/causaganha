---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-qvqmci-check-okf-parser-final"
run_id: "2026-09-09-exciting-mccarthy-qvqmci"
goal_id: "2026-09-09-exciting-mccarthy-qvqmci-goal-stats-coverage-exclude-in-flight"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "{\"concept_count\": 962, \"conformant\": true, \"diagnostics\": [], \"markdown_count\": 965, \"reserved_count\": 3}. First pass after linking goal/decision/evidence/checks flagged the same documented OKF022 gotcha as rounds 14x3v7/kfv7sx/5pmmrp: evidence_id: \"\" on an AgentCheck without evidence is read as a pending FK reference, not absence. Fixed by omitting the field entirely on check-okf-parser-baseline.md and check-ruff-and-contracts.md. Conformant on this re-run, 0 diagnostics."
---

# Check: okf-parser (final da rodada)

Conformante após vincular goal/decisão/evidências/checks. Bateu no gotcha já documentado de `evidence_id: ""` (lido como FK pendente); corrigido omitindo o campo nos dois checks sem evidência associada.
