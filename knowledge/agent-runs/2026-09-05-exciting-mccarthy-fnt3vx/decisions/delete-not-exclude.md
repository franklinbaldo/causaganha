---
type: AgentDecision
id: "2026-09-05-exciting-mccarthy-fnt3vx-decision-delete-not-exclude"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
goal_id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-purge-dead-experiment-imports"
question: "experiments/archive/train_decision_segmenter.py and its .ipynb sibling are kept and explicitly ruff-excluded as 'frozen documentation' (per ruff.toml's own comment, referencing RFC 0001 section 3.5). Should test_all_improvements.py and test_djen_api.py get the same treatment -- add them to extend-exclude and keep them as historical record -- instead of deleting them?"
choice: "Delete both files outright rather than add them to ruff.toml's extend-exclude carve-out."
rationale: "The carve-out that already exists is reserved for artifacts with a documented reason to stay frozen-but-referenced (RFC 0001 section 3.5 explicitly discusses the legacy v5/BIO taxonomy notebooks, and tests/test_notebooks_legacy_taxonomy.py exercises them as a historical contract). test_all_improvements.py and test_djen_api.py have no such role: they are not referenced by any RFC, doc, or test, they import modules that no longer exist anywhere in the tree (not renamed, not relocated -- gone), and nothing exercises or reads them for provenance. CLAUDE.md's project-wide instruction is to delete confirmed-unused code completely rather than keep backwards-compatibility artifacts around; adding an exclude entry would be exactly the kind of unnecessary carve-out that instruction warns against, and would leave misleading, non-runnable code in the tree indefinitely with no plan to ever revisit it."
---

# Decisão: excluir os arquivos, não apenas isentar do ruff

Ao contrário dos notebooks legados (mantidos deliberadamente como documentação histórica, com teste próprio e referência em RFC), estes dois arquivos não têm nenhum papel documental e importam módulos que não existem mais em lugar nenhum do repositório. A escolha é deletar, não isentar.
