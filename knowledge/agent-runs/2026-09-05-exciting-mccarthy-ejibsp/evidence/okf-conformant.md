---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-ejibsp-evidence-okf-conformant"
run_id: "2026-09-05-exciting-mccarthy-ejibsp"
goal_id: "2026-09-05-exciting-mccarthy-ejibsp-goal-extend-completeness-checker"
kind: "okf"
reference: "uv run okf-parser check knowledge --relational-schema okf.schema.sql; uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs"
summary: "okf-parser check: conformant true, concept_count 51, 0 diagnostics — the whole bundle, including both round trees under knowledge/agent-runs/, is structurally valid at the PK/FK level. The project-owned completeness checker, run in directory mode over knowledge/agent-runs, additionally reports every one of the 33 Agent*-typed documents across both rounds as complete (exit 0) — the first real proof the generalized, directory-scanning checker works end to end against real data, not just unit-test fixtures."
---

# Evidência: bundle conformante e árvore completa
