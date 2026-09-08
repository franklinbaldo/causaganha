---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-k18r9l-evidence-red-test"
run_id: "2026-09-08-exciting-mccarthy-k18r9l"
goal_id: "2026-09-08-exciting-mccarthy-k18r9l-goal-readme-optional-contracts-drift"
kind: "test_red"
reference: "uv run pytest -q tests/test_query_readme_contract.py (before the README fix)"
summary: "Failed with: AssertionError: README.md's 'Currently optional' list is stale: missing {'datajud_classes', 'datajud_totals'}, stale entries set(). Confirms the exact staleness two prior rounds (1c7t6u, b4t8pv) had already diagnosed by manual inspection, now demonstrated by an automated cross-check against the real .qmd frontmatter."
---

# Evidence: RED

Teste falhou antes do fix, apontando exatamente `datajud_totals` e `datajud_classes` como ausentes da lista do README.
