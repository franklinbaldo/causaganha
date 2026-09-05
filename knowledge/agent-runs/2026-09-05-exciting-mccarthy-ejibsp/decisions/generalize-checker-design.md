---
type: AgentDecision
id: "2026-09-05-exciting-mccarthy-ejibsp-decision-generalize-checker-design"
run_id: "2026-09-05-exciting-mccarthy-ejibsp"
goal_id: "2026-09-05-exciting-mccarthy-ejibsp-goal-extend-completeness-checker"
question: "Generalize scripts/check_agent_run_completeness.py in place (one dispatch table keyed by concept type, one CLI that also accepts a directory) or add five new sibling scripts/functions, one per type?"
choice: "Generalize in place: REQUIRED_TEXT_FIELDS_BY_TYPE/REQUIRED_LIST_FIELDS_BY_TYPE/ENUM_FIELDS_BY_TYPE dicts keyed by concept type, a single missing_fields_for_type(concept_type, frontmatter) dispatcher, missing_agent_run_fields kept as a thin backward-compatible alias, and main() accepting either a single file (checked against its own declared type) or a directory (scanned recursively, every recognized Agent* document checked, non-Agent* documents silently skipped)."
rationale: "The six tables share the exact same three constraint shapes (required text, required list, enum) declared in knowledge/okf.schema.sql; five near-duplicate scripts would just be the same three loops copy-pasted five times with different field names. A single dispatch table keeps the mirror-the-SQL-contract strategy honest and lets main() run one CLI invocation over an entire knowledge/agent-runs/ tree, which is what .github/workflows/okf.yml needs to gate a whole round's report in one step instead of one call per file per type."
---

# Decisão: generalizar em vez de duplicar

Um dispatcher por tipo, não cinco scripts quase-idênticos; e um modo diretório no `main()`, para que o CI valide a árvore inteira de uma vez.
