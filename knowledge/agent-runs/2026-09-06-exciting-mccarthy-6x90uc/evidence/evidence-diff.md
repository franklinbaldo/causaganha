---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-6x90uc-evidence-diff"
run_id: "2026-09-06-exciting-mccarthy-6x90uc"
goal_id: "2026-09-06-exciting-mccarthy-6x90uc-goal-schema-drift-detection"
kind: "diff"
reference: "git diff -- scripts/check_agent_run_completeness.py tests/test_check_agent_run_completeness.py"
summary: "scripts/check_agent_run_completeness.py: +OPTIONAL_FIELDS_BY_TYPE dict, +declared_fields_for_type(), +unknown_fields_for_type(), main() now also computes and reports `unknown` alongside `missing` and fails (exit 1) if either is non-empty; docstring updated. tests/test_check_agent_run_completeness.py: +1 import, +8 new tests covering the new function directly and through main() over a directory. No other file touched — confirmed scope-confined to this project's own OKF round-report tooling, no production djen_backup/web code affected."
---

# Diff

Só dois arquivos tocados: o checker de completude e seus testes.
