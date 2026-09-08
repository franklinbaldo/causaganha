---
type: AgentCheck
id: "2026-09-08-exciting-mccarthy-5c2heq-check-okf-parser-final"
run_id: "2026-09-08-exciting-mccarthy-5c2heq"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant: true, 0 diagnostics, 828 concepts, 831 markdown files. Run after fixing two schema-field-name mistakes caught by tests/test_check_agent_run_completeness.py (AgentEvidence used 'description' instead of 'summary'; AgentDecision used 'decision'/'reason' instead of 'question'/'choice'/'rationale'). Full pytest -q now green with zero failures (100%, 0 'F' markers), including the three tests that fail while this run.md is mid-draft -- all pass now that completed_at/result_summary/next_move are filled and every OKF instance in this round matches the schema."
---

# Check: okf-parser final

Rodado apos corrigir nomes de campo incorretos em AgentEvidence/AgentDecision (detectados pelo gate de completude). Bundle conformante, 0 diagnosticos. Suite Python completa: 0 falhas.
