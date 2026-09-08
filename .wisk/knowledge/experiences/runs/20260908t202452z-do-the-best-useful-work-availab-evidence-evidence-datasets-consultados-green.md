---
type: "RunEvidence"
id: "run-evidence/20260908t202452z-do-the-best-useful-work-availab/evidence-datasets-consultados-green"
run: "runs/20260908T202452Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "src/causaganha/decisoes/search.py: search_decisions now accumulates datasets_consultados from the datasets it actually iterates (len(datasets) added inside the loop, after the stj-skip continue), instead of reading plan.total_datasets"
summary: "GREEN: both previously-RED tests pass (datasets_consultados == 1), and the full pre-existing suite (tests/causaganha/decisoes/, tests/causaganha_mcp/test_decisoes_buscar*.py, tests/causaganha/processos) still passes -- 19 tests total, no regression. ruff check and ruff format --check both clean on the changed files."
decision: "run-decisions/20260908t202452z-do-the-best-useful-work-availab/decision-datajud-decisoes-clean-fix-scope"
---

# RunEvidence
