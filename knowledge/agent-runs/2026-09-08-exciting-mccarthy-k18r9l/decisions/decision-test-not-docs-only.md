---
type: AgentDecision
id: "2026-09-08-exciting-mccarthy-k18r9l-decision-test-not-docs-only"
run_id: "2026-09-08-exciting-mccarthy-k18r9l"
goal_id: "2026-09-08-exciting-mccarthy-k18r9l-goal-readme-optional-contracts-drift"
question: "Two prior rounds (1c7t6u, b4t8pv) logged the README optional-contracts staleness as a 'one-line docs fix, no behavior change' and left it unselected in favor of TDD-shaped work. Should this round just edit the two missing names, or invest in a regression test?"
choice: "Write a cross-check test (tests/test_query_readme_contract.py) that parses README.md's list and compares it, set-equal, against the real `optional: true` frontmatter across web/src/queries/*.qmd, using scripts/render_queries.py's own parse_qmd(). Fix the two missing names only after confirming the test fails (RED) on the unfixed README."
rationale: "A plain text edit would have fixed today's drift but left the same class of staleness able to recur silently the next time a contract's `optional` flag changes -- which is exactly how this drift happened in the first place (nobody noticed when datajud_totals/datajud_classes were added). The underlying property (which contracts are optional) is already machine-readable via the same parser render_queries.py itself uses in production, so encoding the README's claim as an assertion against that source of truth costs one small test file and converts an indefinitely-recurring manual-sync burden into a one-time fix plus a permanent CI guard. This also gives the change genuine TDD shape (RED confirmed the exact two names already suspected, GREEN after the fix) instead of being an untested prose edit, consistent with this repo's stated TDD-as-default workflow."
---

# Decisao: testar a lista do README contra o frontmatter real, nao so editar

Ver `run.md`/`goals/goal-readme-optional-contracts-drift.md`. Mesma pista logada por duas rodadas anteriores como "docs-only"; resolvida com teste em vez de edicao pura para nao deixar a mesma classe de deriva recorrer sem deteccao.
